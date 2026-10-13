#!/usr/bin/env python3
#
# Compute the inline-filter status and write a filterStatus row:
#   - flow-side degradation: the common-mode flow loss across the lawn (cesped)
#     ensemble (recent solo-run flow vs each valve's station.cleanFlow baseline;
#     "recent" never reaches back past the last cleaning).
#   - odometer: cumulative POC volume (gallons) since the last cleaning.
#   - gauge side: filter resistance R_f and last measured dP from filterReading.
#   - forecast + state (clean | watch | service | sensor). 'sensor': the latest
#     night's lawn runs all read no flow, so the filter can't be judged -- a
#     stalled impeller holding 0 also freezes the odometer. FlowSensorWatch
#     emails about the stall itself.
#   - while the state is 'service', email 'filter' subscribers (root if there
#     are none): at once, then every FILTER.emailDebounceHours. The time each
#     email went out is kept in filterStatus.notified, so a failed send is
#     retried on the next run; logging a cleaning re-arms the first email.
#
# Runs from the OIFilterMonitor systemd timer. --dry-run computes and prints
# without writing/notifying/emailing. Degrades gracefully when a signal is
# missing (no baselines yet -> degradation NULL; no cleaning -> odometer NULL).
# Every FILTER param it reads is checked before anything else runs.
#
# Jun-2026, Pat Welch, pat@mousebrains.com

import argparse
import datetime
import statistics
import sys

import DB
import MyLogger
import Notify
import Params
from filterCommon import cleanSince, loadStations, numericParams, runFlow, soloRuns, volumeSince

RECENT_DAYS = 14    # window for "current" lawn-ensemble flow
REF_FLOW = 12.0     # reference flow (GPM) at which estDP is reported (lawn target)
NIGHT = datetime.timedelta(hours=24)  # "the latest night's runs": within this of the newest
# The daily timer fires about 24 h apart, give or take its accuracy window;
# without slack a 24 h reminder could slip to every other day.
REMIND_SLACK = datetime.timedelta(hours=1)

# FILTER params this script reads: name -> (default, lo, hi)
PARAMS = {
    "warnPct": (10, 0, 100),               # flow loss % for 'watch'
    "servicePct": (18, 0, 100),            # flow loss % for 'service'
    "serviceVolumeGal": (20000, 1, 1e8),   # gallons since cleaning for 'service'
    "emailDebounceHours": (24, 0, 8760),   # hours between service reminders
    "forecastMinDays": (3, 0, 365),        # days since cleaning before forecasting
}


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def recentStart(now, since):
    """Start of the "current flow" window: RECENT_DAYS back, but never before the
    last cleaning -- runs through the old, dirty filter would drag the ensemble
    down and raise a false service alert right after a cleaning."""
    start = now - datetime.timedelta(days=RECENT_DAYS)
    if since is None:
        return start
    if since.tzinfo is None:  # naive --since override: interpret as local time
        since = since.astimezone()
    return max(start, since)


def latestRunsReadZero(runs) -> bool:
    """True if every lawn run within NIGHT of the newest one read no flow.
    `runs` are (tOn, flow) pairs. Valves that draw ~12 GPM showing nothing is
    the sensor (or the supply), not the filter."""
    if not runs:
        return False
    newest = max(t for (t, _) in runs)
    return all(not f or f <= 0 for (t, f) in runs if t > newest - NIGHT)


def flowDegradation(cur, since, logger):
    """Common-mode degradation % across qFilterSensor valves that have a
    cleanFlow baseline and ran recently, and whether the latest of those runs
    all read no flow: (degradation, ensembleFlow, baselineFlow, noFlow), the
    first three None if no data yet."""
    stations = loadStations(cur)
    poc1 = set(stations)
    runs = soloRuns(cur, poc1, recentStart(utcnow(), since))
    ratios, curFlows, baseFlows = [], [], []
    lawnRuns = []   # (tOn, flow) of every baseline-valve run, zero flow included
    for sensor, row in stations.items():
        if not row["qfiltersensor"] or not row["cleanflow"]:
            continue
        runFlows = [(a, runFlow(cur, a, b)) for (a, b) in runs.get(sensor, [])]
        lawnRuns.extend(runFlows)
        flows = [f for (_, f) in runFlows if f and f > 0]
        if not flows:
            continue
        cur_f = statistics.median(flows)
        ratios.append(cur_f / row["cleanflow"])
        curFlows.append(cur_f)
        baseFlows.append(row["cleanflow"])
    noFlow = latestRunsReadZero(lawnRuns)
    if noFlow:
        logger.warning("The latest lawn runs all read no flow: flow sensor stalled?")
    if not ratios:
        logger.info("No recent lawn-ensemble flow (no seeded baselines or no runs)")
        return None, None, None, noFlow
    degradation = max(0.0, (1.0 - statistics.median(ratios)) * 100.0)
    return round(degradation, 1), round(sum(curFlows), 2), round(sum(baseFlows), 2), noFlow


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


def forecast(since, gallons, params, now):
    """Days until serviceVolumeGal at the average rate since the cleaning.
    None until forecastMinDays have passed: right after a cleaning, one heavy
    afternoon (the 1,100-gal test) extrapolates to a few days."""
    serviceVol = params["serviceVolumeGal"]
    if since is None or gallons is None or gallons <= 0 or gallons >= serviceVol:
        return None
    days = (now - since).total_seconds() / 86400.0
    if days <= 0 or days < params["forecastMinDays"]:
        return None
    rate = gallons / days   # gal/day
    return round((serviceVol - gallons) / rate, 1)


def classify(degradation, gallons, params, noFlow=False):
    """State from the automatic signals (flow degradation + odometer). A
    service-level reading stands; otherwise lawn runs that read no flow give
    'sensor' rather than a 'clean' the frozen signals can't back up."""
    serviceVol = params["serviceVolumeGal"]
    service = ((degradation is not None and degradation >= params["servicePct"])
               or (gallons is not None and gallons >= serviceVol))
    watch = ((degradation is not None and degradation >= params["warnPct"])
             or (gallons is not None and gallons >= 0.7 * serviceVol))
    if service:
        return "service"
    if noFlow:
        return "sensor"
    return "watch" if watch else "clean"


def lastNotified(cur, since):
    """When a service email last went out since the cleaning at `since`; None
    if none has. Keyed to the cleaning, not to the state, so neither a
    'sensor' row nor a service/watch flicker re-arms an immediate email."""
    cur.execute("SELECT max(notified) AS t FROM filterStatus WHERE poc=1"
                " AND notified >= COALESCE(%s, '-infinity'::timestamptz);", (since,))
    row = cur.fetchone()
    return row["t"] if row else None


def emailDue(state, last, now, params):
    """Email on entering 'service', then every emailDebounceHours while in it."""
    if state != "service":
        return False
    if last is None:
        return True
    return now - last >= datetime.timedelta(hours=params["emailDebounceHours"]) - REMIND_SLACK


def emailService(cur, info, last, params, args, logger):
    """Email the 'filter' subscribers, or root if there are none. Raises on
    SMTP failure, leaving filterStatus.notified unset for the next run."""
    body = (f"The irrigation inline filter has reached the service threshold.\n\n"
            f"  flow degradation : {info['degradation']}%\n"
            f"  gallons since clean: {info['gallons']}\n"
            f"  est. filter dP    : {info['estDP']} PSI @ {REF_FLOW:.0f} GPM "
            f"(R_f={info['rf']})\n\n"
            f"Clean or replace the filter, then log it in the Filter Log "
            f"(Post-cleaning).\n\n"
            f"This is repeated every {params['emailDebounceHours']:g} hours"
            f" (FILTER.emailDebounceHours) until the filter is serviced.\n")
    subject = "OpenIrrigation: filter needs servicing"
    if last is not None:
        subject += " (reminder)"
    addrs = Notify.sendReport(cur, "filter", subject, body, logger, mailFrom=args.mailFrom)
    logger.info("Emailed the filter service alert to %d address(es)", len(addrs))


def run(args, logger):
    params = numericParams(Params.load(args.db, args.group, logger) or {},
                           args.group, PARAMS)
    now = utcnow()
    with DB.DB(args.db, logger) as db:
        cur = db.cursor(qDict=True)
        since = cleanSince(cur, args.since, logger)

        degradation, ensembleFlow, baselineFlow, noFlow = flowDegradation(cur, since, logger)
        rf, estDP = gaugeState(cur, since)
        gallons = round(volumeSince(cur, since), 0) if since is not None else None
        fcast = forecast(since, gallons, params, now)
        state = classify(degradation, gallons, params, noFlow)

        info = dict(degradation=degradation, ensembleFlow=ensembleFlow,
                    baselineFlow=baselineFlow, gallons=gallons, estDP=estDP,
                    rf=rf, forecast=fcast, state=state)
        logger.info("Filter status: %s", info)

        last = lastNotified(cur, since)
        due = emailDue(state, last, now, params)
        if args.dry_run:
            logger.info("Dry-run: nothing written%s",
                        "; would email the service alert" if due else "")
            return

        cur.execute(
            "INSERT INTO filterStatus(poc,degradation,ensembleFlow,baselineFlow,"
            "gallonsSinceClean,estDP,Rf,forecastDays,state)"
            " VALUES(1,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
            (degradation, ensembleFlow, baselineFlow, gallons, estDP, rf, fcast, state))
        rowID = cur.fetchone()["id"]
        db.execute("SELECT pg_notify('filterstatus_update', %s);", (state,))
        db.commit()

        if not due:
            return
        try:
            emailService(cur, info, last, params, args, logger)
        except Exception:
            logger.exception("Failed to send the filter service email; the next run retries")
            return
        cur.execute("UPDATE filterStatus SET notified=%s WHERE id=%s;", (utcnow(), rowID))
        db.commit()


def main():
    parser = argparse.ArgumentParser(description="OpenIrrigation inline-filter monitor")
    parser.add_argument("--db", required=True, type=str, help="Database name")
    parser.add_argument("--group", default="FILTER", type=str, help="Params group")
    parser.add_argument("--since", type=str,
                        help="Override the cleaning anchor (ISO; naive means local time)")
    parser.add_argument("--mailFrom", type=str, help="email source")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute and print without writing/notifying/emailing")
    MyLogger.addArgs(parser)
    args = parser.parse_args()

    logger = MyLogger.mkLogger(args, __name__, fmt="%(asctime)s: %(levelname)s: %(message)s")
    try:
        run(args, logger)
    except Exception as e:
        logger.exception("Unexpected exception")
        Notify.onException(args, logger, e)
        sys.exit(1)


if __name__ == "__main__":
    main()
