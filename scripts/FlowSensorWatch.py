#!/usr/bin/env python3
#
# Flow-sensor watchdog. Every few minutes, for each POC with a flow sensor:
#
#   no flow     -- valves that should draw at least minExpectedGPM have been
#                  open graceMinutes but the latest reading is <= noFlowGPM:
#                  a stalled or fouled impeller, a valve that did not open,
#                  the supply shut off, or wiring.  -> 'lowFlow' subscribers
#   high flow   -- every open valve has a measured clean-filter baseline
#                  (station.cleanFlow: the solo lawn zones) and every reading
#                  over the last highFlowMinutes is above highFlowPct of it (or
#                  the station's own highFlowFrac): a broken head or pipe.
#                  Gardens and drip are never judged -- their flow depends on
#                  which sections are enabled by hand. A hose bib downstream of
#                  the sensor used during a lawn run also trips it, but lawns
#                  run at night.  -> 'highFlow' subscribers
#
# There is deliberately no "flow with every valve closed" check: the master
# valve is normally open, so the hose bibs downstream of the sensor have water
# whenever they are opened, and hose use would read as a leak.
#
# sensorLog is transition-compressed (TDI.py SensorPoll only writes a fresh
# reading that differs from the last one): a stalled impeller writes nothing,
# and the value from before a valve change holds until the first fresh
# reading, which lagged valve-on by up to ~3.3 min. Hence the grace periods,
# and the high-flow check only trusting readings taken after the open set
# last changed. A sensor that stops reporting while its last value was
# nonzero is not caught -- that value just holds.
#
# Runs from the OIFlowSensorWatch systemd timer. Each alarm is emailed once
# per episode (no flow: until the sensor logs a new reading; high flow: per
# run); the episode keys are kept in a small state file. --dry-run (and --at,
# to evaluate a past moment) print without emailing or touching the state file.
#
# Oct-2026, Pat Welch, pat@mousebrains.com

import argparse
import datetime
import getpass
import json
import logging
import smtplib
import socket
import sys
from email.mime.text import MIMEText

import DB
import MyLogger
import Params


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _minutes(params, name, default):
    return datetime.timedelta(minutes=float(params.get(name, default)))


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


def valvesOn(cur, poc, at):
    """Valves on `poc` that were open at `at`, with their expected flow."""
    cur.execute(
        "SELECT s.name, v.tOn AS ton, s.cleanFlow AS cleanflow,"
        " s.highFlowFrac AS highflowfrac,"
        " COALESCE(s.cleanFlow, s.measuredFlow, s.userFlow, 0) AS expected"
        " FROM " + RUNS +
        " WHERE s.poc=%s AND v.onCode IS NOT NULL AND v.tOn<=%s AND v.tOff>%s"
        " ORDER BY v.tOn;", (poc, at, at))
    return cur.fetchall()


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


def noFlowAlarm(valves, held, at, params):
    """Alarm dict if the open valves should be flowing but the latest reading
    shows no flow, else None. `held` is (timestamp, flow) of that reading."""
    if not valves:
        return None
    expected = sum(float(v["expected"] or 0) for v in valves)
    if expected < float(params.get("minExpectedGPM", 2)):
        return None  # below what the sensor can see (small drip zones)
    since = max(v["ton"] for v in valves)  # when the open set last grew
    if at - since < _minutes(params, "graceMinutes", 6):
        return None  # the first fresh reading can lag valve-on by minutes
    (tRead, flow) = held
    if flow is not None and flow > float(params.get("noFlowGPM", 0.5)):
        return None
    return dict(since=since, minutes=(at - since).total_seconds() / 60.0,
                expected=expected, flow=flow, tRead=tRead,
                valves=[v["name"] for v in valves])


def highFlowAlarm(valves, readings, at, params):
    """Alarm dict if only baseline (cleanFlow) zones are open and the flow has
    stayed above their high-flow limit for the last highFlowMinutes, else None.
    `readings` are the (t, flow) rows logged since the open set last changed,
    oldest first, so a value held over from the previous zone never counts."""
    if not valves or any(v["cleanflow"] is None for v in valves):
        return None  # gardens/drip: no trustworthy expected flow
    since = max(v["ton"] for v in valves)
    if at - since < _minutes(params, "graceMinutes", 6):
        return None
    t0 = at - _minutes(params, "highFlowMinutes", 4)
    if not readings or readings[0][0] > t0:
        return None  # not yet a full window of readings for this set
    pct = float(params.get("highFlowPct", 130))
    expected = sum(float(v["cleanflow"]) for v in valves)
    limit = sum(float(v["cleanflow"]) * float(v["highflowfrac"] or pct) / 100.0
                for v in valves)
    # sample-and-hold: the flow over the window is the reading in force at its
    # start plus every reading inside it
    flows = [f for (t, f) in readings if t <= t0][-1:] + [f for (t, f) in readings if t > t0]
    if any(f is None or f <= limit for f in flows):
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


def _local(t) -> str:
    return t.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z") if t else "never"


def _gpm(f) -> str:
    return "none" if f is None else f"{f:.2f} GPM"


def describe(kind, name, a) -> str:
    """One log line for an alarm."""
    if kind == "noflow":
        return (f"{name}: no flow for {a['minutes']:.0f} min with valves on"
                f" (expected ~{a['expected']:.1f} GPM; last reading {_gpm(a['flow'])}"
                f" at {_local(a['tRead'])}; valves: {', '.join(a['valves'])})")
    return (f"{name}: {_gpm(a['flow'])} to {_gpm(a['peak'])} vs baseline"
            f" {a['expected']:.2f} GPM (limit {a['limit']:.2f}), {a['minutes']:.0f}"
            f" min into the run; valves: {', '.join(a['valves'])}")


def message(kind, name, a) -> tuple:
    """(webList key of the subscribers, subject, body) for an alarm email."""
    if kind == "noflow":
        return ("lowFlow", f"OpenIrrigation: no flow from the {name} flow sensor",
                f"The {name} flow sensor shows no flow, but valves that should draw"
                f" about {a['expected']:.1f} GPM have been on for {a['minutes']:.0f}"
                f" minutes (since {_local(a['since'])}).\n\n"
                f"  valves on    : {', '.join(a['valves'])}\n"
                f"  last reading : {_gpm(a['flow'])} at {_local(a['tRead'])}\n\n"
                "Likely causes: the flow-sensor impeller is stalled or fouled, a"
                " valve did not open, the water supply is shut off, or sensor"
                " wiring. If the heads are running, it is the sensor.\n\n"
                "This is sent once per stall; another arrives only after the"
                " sensor logs a new reading and stalls again.\n")
    valves = ", ".join(a["valves"])
    return ("highFlow", f"OpenIrrigation: high flow on {valves}",
            f"{valves} has run at {_gpm(a['flow'])} to {_gpm(a['peak'])} for"
            f" at least the last few minutes, against a clean baseline of"
            f" {a['expected']:.2f} GPM (alarm limit {a['limit']:.2f} GPM). It"
            f" has been on {a['minutes']:.0f} minutes (since {_local(a['since'])}).\n\n"
            "Likely causes: a broken or missing head, a broken lateral or"
            " pipe, or a hose bib downstream of the flow sensor in use during"
            " the run.\n\nThis is sent once per run.\n")


def subscribers(cur, key) -> list:
    cur.execute("SELECT e.email AS addr FROM emailReports er"
                " JOIN email e ON e.id=er.email"
                " JOIN webList w ON w.id=er.report"
                " WHERE w.grp='reports' AND w.key=%s;", (key,))
    return [r["addr"] for r in cur.fetchall()]


def sendEmail(addrs, subject, body, args) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = args.mailFrom or (getpass.getuser() + "@" + socket.getfqdn())
    msg["To"] = ", ".join(addrs)
    with smtplib.SMTP("localhost", timeout=30) as s:
        s.send_message(msg)


def checkPOC(cur, fs, at, params) -> list:
    """[(kind, episode key, alarm)] for one POC at `at`."""
    poc = fs["poc"]
    valves = valvesOn(cur, poc, at)
    if not valves:
        return []
    out = []
    held = heldReading(cur, fs["pocflow"], at)
    alarm = noFlowAlarm(valves, held, at, params)
    if alarm:
        out.append(("noflow", episodeKey(poc, held[0]), alarm))
    since = max(v["ton"] for v in valves)
    alarm = highFlowAlarm(valves, readingsAfter(cur, fs["pocflow"], since, at),
                          at, params)
    if alarm:
        out.append(("high", f"{poc}@{since.isoformat()}", alarm))
    return out


def run(args, logger):
    params = Params.load(args.db, args.group, logger) or {}
    at = datetime.datetime.fromisoformat(args.at) if args.at else utcnow()
    if at.tzinfo is None:  # naive --at: interpret as local time
        at = at.astimezone()
    readOnly = args.dry_run or args.at is not None
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
                if key == state.get(slot):
                    logger.info("Already alerted (%s): %s", kind, text)
                    continue
                logger.warning("%s: %s", kind.upper(), text)
                if readOnly:
                    continue
                (report, subject, body) = message(kind, fs["name"], alarm)
                addrs = subscribers(cur, report)
                if not addrs:
                    logger.warning("No '%s' email subscribers for the alarm", report)
                else:
                    try:
                        sendEmail(addrs, subject, body, args)
                    except Exception:
                        logger.exception("Failed to send the %s email", kind)
                        continue  # leave the episode un-alerted so the next run retries
                    logger.warning("Emailed %d '%s' subscriber(s)", len(addrs), report)
                state[slot] = key
                changed = True
    if changed:
        saveState(args.state, state)


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
    except Exception:
        logger.exception("Unexpected exception")
        sys.exit(1)


if __name__ == "__main__":
    main()
