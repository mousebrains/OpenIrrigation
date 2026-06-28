#!/usr/bin/env python3
#
# Seed each lawn (cesped) valve's clean-filter baseline flow (station.cleanFlow)
# and flag the lawn solo set as filter sensors (station.qFilterSensor), computed
# from POST-CLEAN solo runs so the baseline reflects a fresh filter.
#
# Dry-run by default; --commit writes the UPDATEs. Run after the filter has been
# cleaned/replaced (logged via a Filter Log "Post-cleaning" entry, or pass
# --since) and a few nights of solo lawn runs have accumulated.
#
# Jun-2026, Pat Welch, pat@mousebrains.com

import argparse
import statistics
import sys

import DB
import MyLogger
import Params
from filterCommon import cleanSince, isLawn, loadStations, runFlow, soloRuns


def computeBaselines(cur, since, minRuns):
    """Per lawn valve: median flow over post-clean solo runs + proposed seeding."""
    stations = loadStations(cur)
    runs = soloRuns(cur, set(stations), since)
    out = []
    for sensor, row in stations.items():
        if not isLawn(row):
            continue
        flows = [f for f in (runFlow(cur, ton, toff)
                             for (ton, toff) in runs.get(sensor, []))
                 if f and f > 0]
        proposed = round(statistics.median(flows), 2) if len(flows) >= minRuns else None
        out.append({"id": row["id"], "name": row["name"],
                    "current": row["cleanflow"], "qfs_current": row["qfiltersensor"],
                    "n": len(flows), "cleanFlow": proposed})
    out.sort(key=lambda x: -(x["cleanFlow"] or 0))
    return out


def report(rows, since, minRuns, logger):
    logger.info("Post-clean solo runs since %s; need >=%d to seed a baseline",
                since, minRuns)
    logger.info("%-22s %4s %10s %12s  qFilterSensor", "valve", "n", "cleanFlow", "(current)")
    for r in rows:
        cf = f"{r['cleanFlow']:.2f}" if r["cleanFlow"] is not None else "(too few)"
        cur = f"{r['current']:.2f}" if r["current"] is not None else "-"
        logger.info("%-22s %4d %10s %12s  %s->True",
                    r["name"][:22], r["n"], cf, cur, r["qfs_current"])


def applyUpdates(db, cur, rows, logger):
    nFlow = nFlag = 0
    for r in rows:
        cur.execute("UPDATE station SET qFilterSensor=TRUE WHERE id=%s;", (r["id"],))
        nFlag += 1
        if r["cleanFlow"] is not None:
            cur.execute("UPDATE station SET cleanFlow=%s WHERE id=%s;",
                        (r["cleanFlow"], r["id"]))
            nFlow += 1
    db.commit()
    logger.info("Committed: qFilterSensor on %d valves, cleanFlow on %d", nFlag, nFlow)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=str, help="Database name")
    parser.add_argument("--group", default="FILTER", type=str, help="Params group")
    parser.add_argument("--since", type=str,
                        help="ISO datetime to count post-clean runs from "
                             "(default: latest Filter Log cleaning)")
    parser.add_argument("--commit", action="store_true",
                        help="Apply the UPDATEs (default: dry-run)")
    MyLogger.addArgs(parser)
    args = parser.parse_args()

    logger = MyLogger.mkLogger(args, __name__, fmt="%(asctime)s: %(levelname)s: %(message)s")
    try:
        params = Params.load(args.db, args.group, logger) or {}
        minRuns = int(params.get("minSoloRuns", 5))
        with DB.DB(args.db, logger) as db:
            cur = db.cursor(qDict=True)
            since = cleanSince(cur, args.since, logger)
            if since is None:
                logger.error("No clean anchor: log a Post-cleaning reading or pass --since")
                sys.exit(2)
            rows = computeBaselines(cur, since, minRuns)
            if not rows:
                logger.warning("No lawn (cesped, poc1, maxCoStations=1) valves found")
                return
            report(rows, since, minRuns, logger)
            if args.commit:
                applyUpdates(db, cur, rows, logger)
            else:
                logger.info("Dry-run: no changes written (use --commit to apply)")
    except SystemExit:
        raise
    except Exception:
        logger.exception("Unexpected exception")
        sys.exit(1)


if __name__ == "__main__":
    main()
