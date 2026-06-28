#
# Shared helpers for the inline-filter scripts (filterBaseline.py, FilterMonitor.py).
# All use a dict-row (qDict=True) cursor.
#
# Jun-2026, Pat Welch, pat@mousebrains.com

import datetime
import statistics

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
    """Timestamp to count runs/volume from: an explicit override, else the most
    recent Filter Log cleaning (qCleaning) event. None if neither exists."""
    if override is not None:
        return datetime.datetime.fromisoformat(override)
    cur.execute("SELECT max(timestamp) AS t FROM filterReading WHERE qCleaning;")
    row = cur.fetchone()
    if row is None or row["t"] is None:
        if logger:
            logger.warning("No cleaning event (filterReading.qCleaning) and no "
                           "override; some outputs will be unavailable.")
        return None
    return row["t"]


def soloRuns(cur, poc1, since) -> dict:
    """{sensor: [(ton,toff), ...]} for POC1 runs since `since` with no
    overlapping POC1 run (so the POC flow during them is that valve's alone)."""
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
    compressed (sample-and-hold): use the rows in the window, else carry the
    last value forward."""
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


def volumeSince(cur, since) -> float:
    """Cumulative POC1 volume (gallons) since `since`, integrating the
    sample-and-hold flow (GPM x minutes held until the next reading)."""
    cur.execute(
        "SELECT timestamp, flow,"
        " lead(timestamp) OVER (ORDER BY timestamp) AS nxt"
        " FROM sensorLog WHERE pocFlow=1 AND timestamp>=%s;", (since,))
    gallons = 0.0
    for r in cur.fetchall():
        if r["nxt"] is not None and r["flow"]:
            dt = (r["nxt"] - r["timestamp"]).total_seconds() / 60.0
            gallons += r["flow"] * dt
    return gallons
