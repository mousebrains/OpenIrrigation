#!/usr/bin/env python3
#
# Flow-sensor watchdog. Every few minutes, for each POC with a flow sensor:
#
#   no flow     -- valves that should draw at least minExpectedGPM have been
#                  open graceMinutes but the latest reading is <= noFlowGPM:
#                  a stalled or fouled impeller, a valve that did not open,
#                  the supply shut off, or wiring.  -> 'lowFlow' subscribers
#   stale       -- the same alarm when the latest reading is nonzero but the
#                  sensor has logged nothing since a valve change that should
#                  have moved the flow by at least minExpectedGPM for at least
#                  graceMinutes: a sensor that stopped reporting mid-flow,
#                  whose last value would otherwise just hold.
#   low flow    -- every open valve has a measured clean-filter baseline
#                  (station.cleanFlow: the solo lawn zones) and every reading
#                  over the last lowFlowMinutes is below lowFlowPct of it (or
#                  the station's own lowFlowFrac; 0 turns it off): a plugged
#                  filter, a valve not opening fully, low supply pressure.
#                  Never raised alongside a no-flow alarm, which takes
#                  precedence.  -> 'lowFlow' subscribers
#   high flow   -- the same zones, every reading over the last highFlowMinutes
#                  above highFlowPct of the baseline (or the station's own
#                  highFlowFrac): a broken head or pipe.
#                  Gardens and drip are never judged on low or high flow --
#                  their flow depends on which sections are enabled by hand. A
#                  hose bib downstream of the sensor used during a lawn run
#                  also trips it, but lawns run at night.  -> 'highFlow'
#
# There is deliberately no "flow with every valve closed" check: the master
# valve is normally open, so the hose bibs downstream of the sensor have water
# whenever they are opened, and hose use would read as a leak.
#
# sensorLog is transition-compressed (TDI.py SensorPoll only writes a fresh
# reading that differs from the last one): a stalled impeller writes nothing,
# and the value from before a valve change holds until the first fresh
# reading, which lagged valve-on by up to ~3.3 min. Hence the grace periods,
# and the low/high-flow checks only trusting readings taken after the open set
# last changed.
#
# Runs from the OIFlowSensorWatch systemd timer. A no-flow alarm is emailed
# once per stall (until the sensor logs a new reading), then again every
# remindHours while the same stall lasts; low and high flow once per run.
# With no subscribers the email goes to root (Notify.sendReport). A failed
# send is retried on the next run. The episode keys are kept in a small state
# file. Every FLOWWATCH param is checked before anything else; a bad one, like
# any other failure, is emailed to the 'systemd' subscribers, the same error
# at most once a day. --dry-run (and --at, to evaluate a past moment) print
# without emailing or touching the state file.
#
# Oct-2026, Pat Welch, pat@mousebrains.com

import argparse
import datetime
import json
import logging
import sys

import DB
import MyLogger
import Notify
import Params
from filterCommon import numericParams

# FLOWWATCH params: name -> (default, lo, hi)
PARAMS = {
    "graceMinutes": (6, 0, 1440),       # valves on this long before judging
    "minExpectedGPM": (2, 0, 1000),     # ignore valve sets drawing less
    "noFlowGPM": (0.5, 0, 1000),        # a reading at or below this is no flow
    "lowFlowPct": (50, 0, 100),         # low flow: % of the cleanFlow baseline
    "lowFlowMinutes": (4, 0, 1440),     # ... sustained this long
    "highFlowPct": (130, 100, 1000),    # high flow: % of the cleanFlow baseline
    "highFlowMinutes": (4, 0, 1440),    # ... sustained this long
    "remindHours": (20, 1, 8760),       # repeat a no-flow alarm while it lasts
}
# Repeat the same failure email at most this often (the timer runs every 2 min)
ERROR_REMIND = datetime.timedelta(hours=24)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _minutes(params, name):
    return datetime.timedelta(minutes=params[name])


def checkParams(raw, group="FLOWWATCH") -> dict:
    """The FLOWWATCH params as floats, defaults filled in; ValueError naming
    the param if one is unusable."""
    return numericParams(raw, group, PARAMS)


def flowSensors(cur):
    """POCs that have a flow sensor."""
    cur.execute("SELECT pf.id AS pocflow, pf.poc, poc.name"
                " FROM pocFlow pf JOIN poc ON poc.id=pf.poc ORDER BY pf.id;")
    return cur.fetchall()


# A valve is open once its on-command completed (onCode set). Finished runs are
# in historical, which also lets --at look back.
RUNS = ("(SELECT sensor, tOn, tOff, onCode FROM action WHERE cmd=0"
        " UNION ALL"
        " SELECT sensor, tOn, tOff, onCode FROM historical) v"
        " JOIN station s ON s.sensor=v.sensor")
EXPECTED = "COALESCE(s.cleanFlow, s.measuredFlow, s.userFlow, 0)"


def valvesOn(cur, poc, at):
    """Valves on `poc` that were open at `at`, with their expected flow."""
    cur.execute(
        "SELECT s.name, v.tOn AS ton, s.cleanFlow AS cleanflow,"
        " s.lowFlowFrac AS lowflowfrac, s.highFlowFrac AS highflowfrac,"
        " " + EXPECTED + " AS expected"
        " FROM " + RUNS +
        " WHERE s.poc=%s AND v.onCode IS NOT NULL AND v.tOn<=%s AND v.tOff>%s"
        " ORDER BY v.tOn;", (poc, at, at))
    return cur.fetchall()


def runsBetween(cur, poc, t0, t1) -> list:
    """(tOn, tOff, expected GPM) of the valve runs on `poc` open at any time
    in [t0, t1]."""
    cur.execute(
        "SELECT v.tOn AS ton, v.tOff AS toff, " + EXPECTED + " AS expected"
        " FROM " + RUNS +
        " WHERE s.poc=%s AND v.onCode IS NOT NULL AND v.tOn<=%s AND v.tOff>%s"
        " ORDER BY v.tOn;", (poc, t1, t0))
    return [(r["ton"], r["toff"], float(r["expected"] or 0)) for r in cur.fetchall()]


def heldReading(cur, pocflow, at) -> tuple:
    """Latest sensorLog reading at or before `at` (sample-and-hold)."""
    cur.execute("SELECT timestamp AS t, flow FROM sensorLog"
                " WHERE pocFlow=%s AND timestamp<=%s"
                " ORDER BY timestamp DESC LIMIT 1;", (pocflow, at))
    row = cur.fetchone()
    return (row["t"], row["flow"]) if row else (None, None)


def readingsAfter(cur, pocflow, t0, at) -> list:
    """sensorLog readings in (t0, at], oldest first."""
    cur.execute("SELECT timestamp AS t, flow FROM sensorLog"
                " WHERE pocFlow=%s AND timestamp>%s AND timestamp<=%s"
                " ORDER BY timestamp;", (pocflow, t0, at))
    return [(r["t"], r["flow"]) for r in cur.fetchall()]


def staleSince(runs, tRead, at, params):
    """When a working sensor would have logged a new reading but this one
    didn't: the start of the first stretch after its latest reading (at
    tRead) during which the open valves' expected flow differed from what it
    was at tRead by at least minExpectedGPM, for at least graceMinutes. None
    if there was no such stretch. `runs` are runsBetween(tRead, at).
    Expected flow is compared with expected flow, never with the reading, so
    a zone running below its baseline isn't mistaken for a dead sensor; and
    two zones of about the same flow back to back, which may log nothing new,
    don't count."""
    if tRead is None:
        return None

    def expectedAt(t):
        return sum(e for (a, b, e) in runs if a <= t < b)

    base = expectedAt(tRead)
    grace = _minutes(params, "graceMinutes")
    edges = sorted({t for (a, b, _) in runs for t in (a, b) if tRead < t < at})
    for (t0, t1) in zip([tRead] + edges, edges + [at], strict=True):
        if t1 - t0 >= grace and abs(expectedAt(t0) - base) >= params["minExpectedGPM"]:
            return t0
    return None


def noFlowAlarm(valves, held, at, params, stale=None):
    """Alarm dict if the open valves should be flowing but the latest reading
    shows no flow, or is a nonzero value the sensor should long since have
    replaced (`stale`, from staleSince), else None. `held` is (timestamp,
    flow) of that reading."""
    if not valves:
        return None
    expected = sum(float(v["expected"] or 0) for v in valves)
    if expected < params["minExpectedGPM"]:
        return None  # below what the sensor can see (small drip zones)
    since = max(v["ton"] for v in valves)  # when the open set last grew
    if at - since < _minutes(params, "graceMinutes"):
        return None  # the first fresh reading can lag valve-on by minutes
    (tRead, flow) = held
    flowing = flow is not None and flow > params["noFlowGPM"]
    if flowing and stale is None:
        return None
    return dict(since=since, minutes=(at - since).total_seconds() / 60.0,
                expected=expected, flow=flow, tRead=tRead,
                stale=stale if flowing else None, change=params["minExpectedGPM"],
                valves=[v["name"] for v in valves])


def windowFlows(valves, readings, at, params, minutesName):
    """(since, flows) over the last `minutesName` minutes for the baseline
    (cleanFlow) zones' low/high checks, or None if they can't be judged: a
    zone without a baseline is open, still in the grace period, or there is
    not yet a full window of readings. `readings` are the (t, flow) rows
    logged since the open set last changed, oldest first, so a value held
    over from the previous zone never counts."""
    if not valves or any(v["cleanflow"] is None for v in valves):
        return None  # gardens/drip: no trustworthy expected flow
    since = max(v["ton"] for v in valves)
    if at - since < _minutes(params, "graceMinutes"):
        return None
    t0 = at - _minutes(params, minutesName)
    if not readings or readings[0][0] > t0:
        return None  # not yet a full window of readings for this set
    # sample-and-hold: the flow over the window is the reading in force at its
    # start plus every reading inside it
    flows = [f for (t, f) in readings if t <= t0][-1:] + [f for (t, f) in readings if t > t0]
    return since, flows


def highFlowAlarm(valves, readings, at, params):
    """Alarm dict if only baseline (cleanFlow) zones are open and the flow has
    stayed above their high-flow limit for the last highFlowMinutes, else None."""
    window = windowFlows(valves, readings, at, params, "highFlowMinutes")
    if window is None:
        return None
    (since, flows) = window
    pct = params["highFlowPct"]
    expected = sum(float(v["cleanflow"]) for v in valves)
    limit = sum(float(v["cleanflow"]) * float(v["highflowfrac"] or pct) / 100.0
                for v in valves)
    if any(f is None or f <= limit for f in flows):
        return None
    return dict(since=since, minutes=(at - since).total_seconds() / 60.0,
                expected=expected, limit=limit, flow=min(flows), peak=max(flows),
                valves=[v["name"] for v in valves])


def lowFlowAlarm(valves, readings, at, params):
    """Alarm dict if only baseline (cleanFlow) zones are open and the flow has
    stayed below their low-flow limit for the last lowFlowMinutes, else None.
    A station's lowFlowFrac overrides lowFlowPct; 0 turns the check off."""
    window = windowFlows(valves, readings, at, params, "lowFlowMinutes")
    if window is None:
        return None
    (since, flows) = window
    expected = sum(float(v["cleanflow"]) for v in valves)
    if expected < params["minExpectedGPM"]:
        return None  # below what the sensor can see
    limit = sum(float(v["cleanflow"]) / 100.0
                * float(params["lowFlowPct"] if v["lowflowfrac"] is None else v["lowflowfrac"])
                for v in valves)
    if any(f is None or f >= limit for f in flows):
        return None
    return dict(since=since, minutes=(at - since).total_seconds() / 60.0,
                expected=expected, limit=limit, flow=min(flows), peak=max(flows),
                valves=[v["name"] for v in valves])


def episodeKey(poc, tRead) -> str:
    """One stall = no new reading since tRead, however many runs it spans."""
    return f"{poc}@{tRead.isoformat() if tRead is not None else 'none'}"


def loadState(path):
    try:
        with open(path) as fp:
            return json.load(fp)
    except (OSError, ValueError):
        return {}


def saveState(path, state) -> None:
    with open(path, "w") as fp:
        json.dump(state, fp)


def alerted(state, slot) -> tuple:
    """(episode key, when last emailed) recorded for `slot`. A bare key is
    the format from before reminders, with no time."""
    val = state.get(slot)
    if isinstance(val, dict):
        sent = val.get("sent")
        return (val.get("key"), datetime.datetime.fromisoformat(sent) if sent else None)
    return (val, None)


def _local(t) -> str:
    return t.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z") if t else "never"


def _gpm(f) -> str:
    return "none" if f is None else f"{f:.2f} GPM"


def describe(kind, name, a) -> str:
    """One log line for an alarm."""
    if kind == "noflow" and a["stale"]:
        return (f"{name}: no new reading since {_local(a['tRead'])} ({_gpm(a['flow'])})"
                f" though the flow should have changed by {_local(a['stale'])};"
                f" valves on {a['minutes']:.0f} min (expected ~{a['expected']:.1f} GPM):"
                f" {', '.join(a['valves'])}")
    if kind == "noflow":
        return (f"{name}: no flow for {a['minutes']:.0f} min with valves on"
                f" (expected ~{a['expected']:.1f} GPM; last reading {_gpm(a['flow'])}"
                f" at {_local(a['tRead'])}; valves: {', '.join(a['valves'])})")
    return (f"{name}: {_gpm(a['flow'])} to {_gpm(a['peak'])} vs baseline"
            f" {a['expected']:.2f} GPM ({kind} limit {a['limit']:.2f}), {a['minutes']:.0f}"
            f" min into the run; valves: {', '.join(a['valves'])}")


def message(kind, name, a, remindHours=PARAMS["remindHours"][0], reminder=False) -> tuple:
    """(webList key of the subscribers, subject, body) for an alarm email."""
    valves = ", ".join(a["valves"])
    if kind == "noflow":
        again = (f"This is repeated every {remindHours:g} hours while the same"
                 " stall lasts; a new stall, after the sensor logs a fresh"
                 " reading, is reported at once.\n")
        tag = " (reminder)" if reminder else ""
        if a["stale"]:
            return ("lowFlow", f"OpenIrrigation: the {name} flow sensor has stopped reporting{tag}",
                    f"The {name} flow sensor has logged nothing since"
                    f" {_local(a['tRead'])}, when it read {_gpm(a['flow'])}. The"
                    f" valves since then should have changed the flow by at least"
                    f" {a['change']:g} GPM from {_local(a['stale'])}, so a working"
                    " sensor would have logged a new reading. Valves that should"
                    f" draw about {a['expected']:.1f} GPM have been on for"
                    f" {a['minutes']:.0f} minutes (since {_local(a['since'])}).\n\n"
                    f"  valves on    : {valves}\n"
                    f"  last reading : {_gpm(a['flow'])} at {_local(a['tRead'])}\n\n"
                    "Likely causes: the controller is no longer polling the sensor"
                    " (see the TDI log), sensor wiring, or the sensor's decoder."
                    " Flow alarms and the filter odometer are blind until it"
                    " reports again.\n\n" + again)
        return ("lowFlow", f"OpenIrrigation: no flow from the {name} flow sensor{tag}",
                f"The {name} flow sensor shows no flow, but valves that should draw"
                f" about {a['expected']:.1f} GPM have been on for {a['minutes']:.0f}"
                f" minutes (since {_local(a['since'])}).\n\n"
                f"  valves on    : {valves}\n"
                f"  last reading : {_gpm(a['flow'])} at {_local(a['tRead'])}\n\n"
                "Likely causes: the flow-sensor impeller is stalled or fouled, a"
                " valve did not open, the water supply is shut off, or sensor"
                " wiring. If the heads are running, it is the sensor.\n\n" + again)
    if kind == "low":
        return ("lowFlow", f"OpenIrrigation: low flow on {valves}",
                f"{valves} has run at {_gpm(a['flow'])} to {_gpm(a['peak'])} for"
                f" at least the last few minutes, against a clean baseline of"
                f" {a['expected']:.2f} GPM (alarm limit {a['limit']:.2f} GPM). It"
                f" has been on {a['minutes']:.0f} minutes (since {_local(a['since'])}).\n\n"
                "Likely causes: a plugged inline filter, a valve not opening fully,"
                " low supply pressure, or a fouled flow-sensor impeller reading"
                " low.\n\nThis is sent once per run.\n")
    return ("highFlow", f"OpenIrrigation: high flow on {valves}",
            f"{valves} has run at {_gpm(a['flow'])} to {_gpm(a['peak'])} for"
            f" at least the last few minutes, against a clean baseline of"
            f" {a['expected']:.2f} GPM (alarm limit {a['limit']:.2f} GPM). It"
            f" has been on {a['minutes']:.0f} minutes (since {_local(a['since'])}).\n\n"
            "Likely causes: a broken or missing head, a broken lateral or"
            " pipe, or a hose bib downstream of the flow sensor in use during"
            " the run.\n\nThis is sent once per run.\n")


def checkPOC(cur, fs, at, params) -> list:
    """[(kind, episode key, alarm)] for one POC at `at`."""
    poc = fs["poc"]
    valves = valvesOn(cur, poc, at)
    if not valves:
        return []
    out = []
    held = heldReading(cur, fs["pocflow"], at)
    stale = None
    if held[1] is not None and held[1] > params["noFlowGPM"]:
        stale = staleSince(runsBetween(cur, poc, held[0], at), held[0], at, params)
    noFlow = noFlowAlarm(valves, held, at, params, stale)
    if noFlow:
        out.append(("noflow", episodeKey(poc, held[0]), noFlow))
    since = max(v["ton"] for v in valves)
    readings = readingsAfter(cur, fs["pocflow"], since, at)
    alarm = highFlowAlarm(valves, readings, at, params)
    if alarm:
        out.append(("high", f"{poc}@{since.isoformat()}", alarm))
    alarm = None if noFlow else lowFlowAlarm(valves, readings, at, params)
    if alarm:  # never alongside no flow, which takes precedence
        out.append(("low", f"{poc}@{since.isoformat()}", alarm))
    return out


def run(args, logger):
    params = checkParams(Params.load(args.db, args.group, logger) or {}, args.group)
    at = datetime.datetime.fromisoformat(args.at) if args.at else utcnow()
    if at.tzinfo is None:  # naive --at: interpret as local time
        at = at.astimezone()
    readOnly = args.dry_run or args.at is not None
    remind = datetime.timedelta(hours=params["remindHours"])
    state = loadState(args.state)
    changed = False
    with DB.DB(args.db, logger) as db:
        cur = db.cursor(qDict=True)
        for fs in flowSensors(cur):
            alarms = checkPOC(cur, fs, at, params)
            if not alarms:
                logger.info("%s: OK", fs["name"])
            for (kind, key, alarm) in alarms:
                text = describe(kind, fs["name"], alarm)
                slot = f"{kind}:{fs['poc']}"
                (prevKey, sent) = alerted(state, slot)
                reminder = key == prevKey
                if reminder and (kind != "noflow" or (sent is not None and at - sent < remind)):
                    logger.info("Already alerted (%s): %s", kind, text)
                    continue
                logger.warning("%s%s: %s", kind.upper(), " (reminder)" if reminder else "", text)
                if readOnly:
                    continue
                (report, subject, body) = message(kind, fs["name"], alarm,
                                                  params["remindHours"], reminder)
                try:
                    addrs = Notify.sendReport(cur, report, subject, body, logger,
                                              mailFrom=args.mailFrom)
                except Exception:
                    logger.exception("Failed to send the %s email", kind)
                    continue  # leave the episode un-alerted so the next run retries
                logger.warning("Emailed %d address(es) for the '%s' report", len(addrs), report)
                state[slot] = {"key": key, "sent": at.isoformat()}
                changed = True
    if changed:
        saveState(args.state, state)


def reportError(path, exc, now) -> bool:
    """True if `exc` should be emailed: not the same error as one already
    emailed within ERROR_REMIND. Records it in the state file if so."""
    text = f"{type(exc).__name__}: {exc}"
    state = loadState(path)
    prev = state.get("error")
    if isinstance(prev, dict) and prev.get("text") == text and prev.get("sent") \
            and now - datetime.datetime.fromisoformat(prev["sent"]) < ERROR_REMIND:
        return False
    state["error"] = {"text": text, "sent": now.isoformat()}
    try:
        saveState(path, state)
    except OSError:
        pass  # better a repeated email than none
    return True


def main():
    parser = argparse.ArgumentParser(description="OpenIrrigation flow-sensor watchdog")
    parser.add_argument("--db", required=True, type=str, help="Database name")
    parser.add_argument("--group", default="FLOWWATCH", type=str, help="Params group")
    parser.add_argument("--state", default="FlowSensorWatch.state", type=str,
                        help="File remembering the episodes already alerted")
    parser.add_argument("--at", type=str,
                        help="Evaluate at this past time (ISO); implies --dry-run")
    parser.add_argument("--mailFrom", type=str, help="email source")
    parser.add_argument("--dry-run", action="store_true",
                        help="Evaluate and print without emailing or saving state")
    MyLogger.addArgs(parser)
    args = parser.parse_args()

    logger = MyLogger.mkLogger(args, __name__, fmt="%(asctime)s: %(levelname)s: %(message)s")
    if not (args.verbose or args.dry_run or args.at):
        # Runs every few minutes: keep the routine "OK" lines out of the log
        logger.setLevel(logging.WARNING)
    try:
        run(args, logger)
    except Exception as e:
        logger.exception("Unexpected exception")
        if not (args.dry_run or args.at) and reportError(args.state, e, utcnow()):
            Notify.onException(args, logger, e)
        sys.exit(1)


if __name__ == "__main__":
    main()
