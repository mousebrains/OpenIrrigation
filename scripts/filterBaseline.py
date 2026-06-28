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
import datetime
import statistics
import sys

import DB
import MyLogger
import Params

SETTLE = datetime.timedelta(seconds=90)  # let flow stabilise after valve-on


def isLawn(row) -> bool:
    """The solo lawn (cesped) valves on POC1 are the filter sensors."""
    return (str(row["name"]).lower().startswith("cesped")
            and row["poc"] == 1
            and row["maxcostations"] == 1)


def loadStations(cur) -> dict:
    """sensor id -> station row, for POC1 stations."""
    cur.execute("SELECT id,sensor,name,poc,maxcostations,cleanflow,qfiltersensor"
                " FROM station WHERE poc=1;")
    return {r["sensor"]: r for r in cur.fetchall()}


def cleanSince(cur, override, logger):
    """Count runs from --since, else the most recent Filter Log cleaning event."""
    if override is not None:
        return datetime.datetime.fromisoformat(override)
    cur.execute("SELECT max(timestamp) AS t FROM filterReading WHERE qCleaning;")
    row = cur.fetchone()
    if row is None or row["t"] is None:
        logger.error("No cleaning event in filterReading (qCleaning) and no "
                     "--since given; log a Post-cleaning reading or pass --since.")
        return None
    return row["t"]


def soloRuns(cur, poc1, since) -> dict:
    """{sensor: [(ton,toff), ...]} for POC1 runs with no overlapping POC1 run."""
    cur.execute("SELECT sensor,ton,toff FROM historical"
                " WHERE toff>=%s ORDER BY ton;", (since,))
    runs = [(r["sensor"], r["ton"], r["toff"]) for r in cur.fetchall()
            if r["sensor"] in poc1]
    out: dict = {}
    n = len(runs)
    for i, (s, a, b) in enumerate(runs):
        solo = True
        for j in range(n):
            if j == i:
                continue
            (s2, a2, b2) = runs[j]
            if a2 > b:
                break
            if a < b2 and a2 < b:  # overlap
                solo = False
                break
        if solo:
            out.setdefault(s, []).append((a, b))
    return out


def runFlow(cur, ton, toff):
    """Steady flow over the settled part of a run. sensorLog is transition-
    compressed (sample-and-hold), so use the rows in the window, and if there
    are none (a rock-steady run) carry the last value forward."""
    cur.execute("SELECT flow FROM sensorLog WHERE pocFlow=1"
                " AND timestamp BETWEEN %s AND %s;", (ton + SETTLE, toff))
    vals = [r["flow"] for r in cur.fetchall() if r["flow"] is not None]
    if vals:
        return statistics.median(vals)
    mid = ton + (toff - ton) / 2
    cur.execute("SELECT flow FROM sensorLog WHERE pocFlow=1 AND timestamp<=%s"
                " ORDER BY timestamp DESC LIMIT 1;", (mid,))
    row = cur.fetchone()
    return row["flow"] if row and row["flow"] is not None else None


def computeBaselines(cur, logger, since, minRuns):
    """Return list of dicts: per lawn valve, the proposed cleanFlow + qFilterSensor."""
    stations = loadStations(cur)
    poc1 = set(stations)
    runs = soloRuns(cur, poc1, since)

    out = []
    for sensor, row in stations.items():
        if not isLawn(row):
            continue
        flows = []
        for (ton, toff) in runs.get(sensor, []):
            f = runFlow(cur, ton, toff)
            if f is not None and f > 0:
                flows.append(f)
        proposed = round(statistics.median(flows), 2) if len(flows) >= minRuns else None
        out.append({
            "id": row["id"], "name": row["name"],
            "current": row["cleanflow"], "qfs_current": row["qfiltersensor"],
            "n": len(flows), "cleanFlow": proposed,
        })
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


def apply(db, cur, rows, logger):
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
                sys.exit(2)
            rows = computeBaselines(cur, logger, since, minRuns)
            if not rows:
                logger.warning("No lawn (cesped, poc1, maxCoStations=1) valves found")
                return
            report(rows, since, minRuns, logger)
            if args.commit:
                apply(db, cur, rows, logger)
            else:
                logger.info("Dry-run: no changes written (use --commit to apply)")
    except SystemExit:
        raise
    except Exception:
        logger.exception("Unexpected exception")
        sys.exit(1)


if __name__ == "__main__":
    main()
