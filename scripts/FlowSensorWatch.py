#!/usr/bin/env python3
#
# Flow-sensor watchdog: alarm when valves that should be drawing water have
# been on for a while but their POC's flow sensor shows no flow.
#
# sensorLog is transition-compressed (TDI.py SensorPoll only writes a fresh
# reading that differs from the last one), so a stalled impeller writes
# nothing: the 0 logged when the previous run ended simply holds. The check is
# therefore on the held (latest) reading: the open valves should draw at least
# minExpectedGPM, the set has been unchanged for graceMinutes, and the latest
# reading is <= noFlowGPM. The grace covers the controller's lag between a
# valve opening and its first fresh reading (up to ~3.3 min observed).
#
# The same symptom has other causes: a valve that did not open, the supply
# shut off, or sensor/decoder wiring. A sensor that stops reporting while its
# last value was nonzero is NOT caught -- that value just holds.
#
# Runs every few minutes from the OIFlowSensorWatch systemd timer and emails
# 'lowFlow' subscribers once per stall: the episode key is the timestamp of
# the last reading, kept in a small state file, so a sensor that stays dead
# across many runs sends one email. --dry-run (and --at, to evaluate a past
# moment) print without emailing or touching the state file.
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


def flowSensors(cur):
    """POCs that have a flow sensor."""
    cur.execute("SELECT pf.id AS pocflow, pf.poc, poc.name"
                " FROM pocFlow pf JOIN poc ON poc.id=pf.poc ORDER BY pf.id;")
    return cur.fetchall()


def valvesOn(cur, poc, at):
    """Valves on `poc` that were open at `at`, with their expected flow. A valve
    is open once its on-command completed (onCode set); finished runs are in
    historical, which also lets --at look back."""
    cur.execute(
        "SELECT s.name, v.tOn AS ton,"
        " COALESCE(s.cleanFlow, s.measuredFlow, s.userFlow, 0) AS expected"
        " FROM (SELECT sensor, tOn, tOff, onCode FROM action WHERE cmd=0"
        "       UNION ALL"
        "       SELECT sensor, tOn, tOff, onCode FROM historical) v"
        " JOIN station s ON s.sensor=v.sensor"
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


def evaluate(valves, held, at, params):
    """Alarm dict if the open valves should be flowing but the latest reading
    shows no flow, else None. `held` is (timestamp, flow) of that reading."""
    if not valves:
        return None
    expected = sum(float(v["expected"] or 0) for v in valves)
    if expected < float(params.get("minExpectedGPM", 2)):
        return None  # below what the sensor can see (small drip zones)
    since = max(v["ton"] for v in valves)  # when the open set last grew
    grace = datetime.timedelta(minutes=float(params.get("graceMinutes", 6)))
    if at - since < grace:
        return None  # the first fresh reading can lag valve-on by minutes
    (tRead, flow) = held
    if flow is not None and flow > float(params.get("noFlowGPM", 0.5)):
        return None
    return dict(since=since, minutes=(at - since).total_seconds() / 60.0,
                expected=expected, flow=flow, tRead=tRead,
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


def subscribers(cur) -> list:
    cur.execute("SELECT e.email AS addr FROM emailReports er"
                " JOIN email e ON e.id=er.email"
                " JOIN webList w ON w.id=er.report"
                " WHERE w.grp='reports' AND w.key='lowFlow';")
    return [r["addr"] for r in cur.fetchall()]


def _local(t) -> str:
    return t.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z") if t else "never"


def describe(name, alarm) -> str:
    flow = "none" if alarm["flow"] is None else f"{alarm['flow']:.2f} GPM"
    return (f"{name}: no flow for {alarm['minutes']:.0f} min with valves on"
            f" (expected ~{alarm['expected']:.1f} GPM; last reading {flow}"
            f" at {_local(alarm['tRead'])}; valves: {', '.join(alarm['valves'])})")


def emailAlarm(addrs, name, alarm, args) -> None:
    flow = "none" if alarm["flow"] is None else f"{alarm['flow']:.2f} GPM"
    body = (f"The {name} flow sensor shows no flow, but valves that should draw"
            f" about {alarm['expected']:.1f} GPM have been on for"
            f" {alarm['minutes']:.0f} minutes (since {_local(alarm['since'])}).\n\n"
            f"  valves on    : {', '.join(alarm['valves'])}\n"
            f"  last reading : {flow} at {_local(alarm['tRead'])}\n\n"
            "Likely causes: the flow-sensor impeller is stalled or fouled, a"
            " valve did not open, the water supply is shut off, or sensor"
            " wiring. If the heads are running, it is the sensor.\n\n"
            "This is sent once per stall; another arrives only after the"
            " sensor logs a new reading and stalls again.\n")
    msg = MIMEText(body)
    msg["Subject"] = f"OpenIrrigation: no flow from the {name} flow sensor"
    msg["From"] = args.mailFrom or (getpass.getuser() + "@" + socket.getfqdn())
    msg["To"] = ", ".join(addrs)
    with smtplib.SMTP("localhost", timeout=30) as s:
        s.send_message(msg)


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
            valves = valvesOn(cur, fs["poc"], at)
            held = heldReading(cur, fs["pocflow"], at)
            alarm = evaluate(valves, held, at, params)
            if alarm is None:
                logger.info("%s: OK (%d valve(s) on, last reading %s GPM)",
                            fs["name"], len(valves),
                            "none" if held[1] is None else f"{held[1]:.2f}")
                continue
            key = episodeKey(fs["poc"], held[0])
            if key == state.get(str(fs["poc"])):
                logger.info("Still stalled, already alerted: %s",
                            describe(fs["name"], alarm))
                continue
            logger.warning("NO FLOW: %s", describe(fs["name"], alarm))
            if readOnly:
                continue
            addrs = subscribers(cur)
            if not addrs:
                logger.warning("No 'lowFlow' email subscribers for the alarm")
            else:
                try:
                    emailAlarm(addrs, fs["name"], alarm, args)
                except Exception:
                    logger.exception("Failed to send the no-flow email")
                    continue  # leave the episode un-alerted so the next run retries
                logger.warning("Emailed %d 'lowFlow' subscriber(s)", len(addrs))
            state[str(fs["poc"])] = key
            changed = True
    if changed:
        saveState(args.state, state)


def main():
    parser = argparse.ArgumentParser(description="OpenIrrigation flow-sensor watchdog")
    parser.add_argument("--db", required=True, type=str, help="Database name")
    parser.add_argument("--group", default="FLOWWATCH", type=str, help="Params group")
    parser.add_argument("--state", default="FlowSensorWatch.state", type=str,
                        help="File remembering the last stall alerted")
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
