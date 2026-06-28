#!/usr/bin/env python3
#
# Compute the inline-filter status and write a filterStatus row:
#   - flow-side degradation: the common-mode flow loss across the lawn (cesped)
#     ensemble (recent solo-run flow vs each valve's station.cleanFlow baseline).
#   - odometer: cumulative POC volume (gallons) since the last cleaning.
#   - gauge side: filter resistance R_f and last measured dP from filterReading.
#   - forecast + state (clean | watch | service), emailing 'filter' subscribers
#     on the transition into 'service'.
#
# Runs from the OIFilterMonitor systemd timer. --dry-run computes and prints
# without writing/notifying/emailing. Degrades gracefully when a signal is
# missing (no baselines yet -> degradation NULL; no cleaning -> odometer NULL).
#
# Jun-2026, Pat Welch, pat@mousebrains.com

import argparse
import datetime
import getpass
import smtplib
import socket
import statistics
import sys
from email.mime.text import MIMEText

import DB
import MyLogger
import Params
from filterCommon import cleanSince, loadStations, runFlow, soloRuns, volumeSince

RECENT_DAYS = 14    # window for "current" lawn-ensemble flow
REF_FLOW = 12.0     # reference flow (GPM) at which estDP is reported (lawn target)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def flowDegradation(cur, logger):
    """Common-mode degradation % across qFilterSensor valves that have a
    cleanFlow baseline and ran recently. (None, None, None) if no data yet."""
    stations = loadStations(cur)
    poc1 = set(stations)
    runs = soloRuns(cur, poc1, utcnow() - datetime.timedelta(days=RECENT_DAYS))
    ratios, curFlows, baseFlows = [], [], []
    for sensor, row in stations.items():
        if not row["qfiltersensor"] or not row["cleanflow"]:
            continue
        flows = [f for f in (runFlow(cur, a, b) for (a, b) in runs.get(sensor, []))
                 if f and f > 0]
        if not flows:
            continue
        cur_f = statistics.median(flows)
        ratios.append(cur_f / row["cleanflow"])
        curFlows.append(cur_f)
        baseFlows.append(row["cleanflow"])
    if not ratios:
        logger.info("No recent lawn-ensemble flow (no seeded baselines or no runs)")
        return None, None, None
    degradation = max(0.0, (1.0 - statistics.median(ratios)) * 100.0)
    return round(degradation, 1), round(sum(curFlows), 2), round(sum(baseFlows), 2)


def gaugeState(cur, since):
    """R_f (median of recent gauge readings) and last measured dP (PSI)."""
    cur.execute("SELECT upstreamPSI-downstreamPSI AS dp, flow FROM filterReading"
                " WHERE qCleaning IS NOT TRUE AND flow > 0.5"
                " AND upstreamPSI IS NOT NULL AND downstreamPSI IS NOT NULL"
                " AND timestamp >= COALESCE(%s, '-infinity'::timestamptz)"
                " ORDER BY timestamp DESC LIMIT 10;", (since,))
    rows = cur.fetchall()
    if not rows:
        return None, None
    rf = statistics.median([r["dp"] / (r["flow"] * r["flow"]) for r in rows])
    estDP = round(rf * REF_FLOW * REF_FLOW, 1)   # dP a REF_FLOW-GPM valve would see
    return round(rf, 4), estDP


def forecast(cur, since, gallons, params):
    """Days until serviceVolumeGal at the recent through-the-filter rate."""
    serviceVol = float(params.get("serviceVolumeGal", 20000))
    if since is None or gallons is None or gallons <= 0 or gallons >= serviceVol:
        return None
    days = max(1e-6, (utcnow() - since).total_seconds() / 86400.0)
    rate = gallons / days   # gal/day
    return round((serviceVol - gallons) / rate, 1) if rate > 0 else None


def classify(degradation, gallons, params):
    """State from the automatic signals (flow degradation + odometer)."""
    warnPct = float(params.get("warnPct", 10))
    servicePct = float(params.get("servicePct", 18))
    serviceVol = float(params.get("serviceVolumeGal", 20000))
    service = ((degradation is not None and degradation >= servicePct)
               or (gallons is not None and gallons >= serviceVol))
    watch = ((degradation is not None and degradation >= warnPct)
             or (gallons is not None and gallons >= 0.7 * serviceVol))
    return "service" if service else ("watch" if watch else "clean")


def priorState(cur):
    cur.execute("SELECT state FROM filterStatus WHERE poc=1"
                " ORDER BY timestamp DESC LIMIT 1;")
    row = cur.fetchone()
    return row["state"] if row else None


def emailService(cur, info, args, logger):
    cur.execute("SELECT e.email AS addr FROM emailReports er"
                " JOIN email e ON e.id=er.email"
                " JOIN webList w ON w.id=er.report"
                " WHERE w.grp='reports' AND w.key='filter';")
    addrs = [r["addr"] for r in cur.fetchall()]
    if not addrs:
        logger.info("Filter at service threshold but no 'filter' email subscribers")
        return
    body = (f"The irrigation inline filter has reached the service threshold.\n\n"
            f"  flow degradation : {info['degradation']}%\n"
            f"  gallons since clean: {info['gallons']}\n"
            f"  est. filter dP    : {info['estDP']} PSI @ {REF_FLOW:.0f} GPM "
            f"(R_f={info['rf']})\n\n"
            f"Clean or replace the filter, then log it in the Filter Log "
            f"(Post-cleaning).\n")
    msg = MIMEText(body)
    msg["Subject"] = "OpenIrrigation: filter needs servicing"
    msg["From"] = args.mailFrom or (getpass.getuser() + "@" + socket.getfqdn())
    msg["To"] = ", ".join(addrs)
    with smtplib.SMTP("localhost", timeout=30) as s:
        s.send_message(msg)
    logger.info("Emailed %d filter subscriber(s)", len(addrs))


def run(args, logger):
    params = Params.load(args.db, args.group, logger) or {}
    with DB.DB(args.db, logger) as db:
        cur = db.cursor(qDict=True)
        since = cleanSince(cur, args.since, logger)

        degradation, ensembleFlow, baselineFlow = flowDegradation(cur, logger)
        rf, estDP = gaugeState(cur, since)
        gallons = round(volumeSince(cur, since), 0) if since is not None else None
        fcast = forecast(cur, since, gallons, params)
        state = classify(degradation, gallons, params)

        info = dict(degradation=degradation, ensembleFlow=ensembleFlow,
                    baselineFlow=baselineFlow, gallons=gallons, estDP=estDP,
                    rf=rf, forecast=fcast, state=state)
        logger.info("Filter status: %s", info)

        if args.dry_run:
            logger.info("Dry-run: nothing written")
            return

        prior = priorState(cur)
        cur.execute(
            "INSERT INTO filterStatus(poc,degradation,ensembleFlow,baselineFlow,"
            "gallonsSinceClean,estDP,Rf,forecastDays,state)"
            " VALUES(1,%s,%s,%s,%s,%s,%s,%s,%s);",
            (degradation, ensembleFlow, baselineFlow, gallons, estDP, rf, fcast, state))
        db.execute("SELECT pg_notify('filterstatus_update', %s);", (state,))
        db.commit()

        if state == "service" and prior != "service":
            try:
                emailService(cur, info, args, logger)
            except Exception:
                logger.exception("Failed to send filter service email")


def main():
    parser = argparse.ArgumentParser(description="OpenIrrigation inline-filter monitor")
    parser.add_argument("--db", required=True, type=str, help="Database name")
    parser.add_argument("--group", default="FILTER", type=str, help="Params group")
    parser.add_argument("--since", type=str, help="Override the cleaning anchor (ISO)")
    parser.add_argument("--mailFrom", type=str, help="email source")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute and print without writing/notifying/emailing")
    MyLogger.addArgs(parser)
    args = parser.parse_args()

    logger = MyLogger.mkLogger(args, __name__, fmt="%(asctime)s: %(levelname)s: %(message)s")
    try:
        run(args, logger)
    except Exception:
        logger.exception("Unexpected exception")
        sys.exit(1)


if __name__ == "__main__":
    main()
