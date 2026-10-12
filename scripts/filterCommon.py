#
# Shared helpers for the inline-filter scripts (filterBaseline.py, FilterMonitor.py)
# and the flow-sensor watchdog (FlowSensorWatch.py, numericParams only).
# All use a dict-row (qDict=True) cursor.
#
# Jun-2026, Pat Welch, pat@mousebrains.com

import datetime
import math
import statistics

SETTLE = datetime.timedelta(seconds=90)  # let flow stabilise after valve-on
# Longest a held sensorLog reading is integrated for. A sensor that stops
# reporting mid-flow leaves its last value held until it next logs; uncapped,
# a dead day at 12.6 GPM adds 18,000 phantom gallons (a false 'service'). The
# cost: a real flow steady for longer than this without one new reading (a
# long drip run) is under-counted.
MAX_HOLD = datetime.timedelta(minutes=60)


def numericParams(raw, group, spec) -> dict:
    """Validate and coerce a params group up front, so a bad value fails the
    run at once, naming the param, instead of only once the code path that
    reads it is reached (e.g. with valves open). `raw` is Params.load()'s
    dict; `spec` maps name -> (default, lo, hi). A missing row takes its
    default; an empty, non-numeric or out-of-range value raises ValueError.
    Params.load() turns '0,5' and '20,000' into lists, which are rejected."""
    out = {}
    for name, (default, lo, hi) in spec.items():
        val = raw.get(name, default)
        if isinstance(val, bool) or not isinstance(val, (int, float)) \
                or not math.isfinite(val) or not lo <= val <= hi:
            raise ValueError(f"params {group}.{name}={val!r}:"
                             f" expected a number from {lo:g} to {hi:g}")
        out[name] = float(val)
    return out


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
        t = datetime.datetime.fromisoformat(override)
        return t if t.tzinfo is not None else t.astimezone()  # naive: local time
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
    sample-and-hold flow (GPM x minutes held until the next reading, at most
    MAX_HOLD)."""
    cur.execute(
        "SELECT timestamp, flow,"
        " lead(timestamp) OVER (ORDER BY timestamp) AS nxt"
        " FROM sensorLog WHERE pocFlow=1 AND timestamp>=%s;", (since,))
    gallons = 0.0
    for r in cur.fetchall():
        if r["nxt"] is not None and r["flow"]:
            dt = min(r["nxt"] - r["timestamp"], MAX_HOLD).total_seconds() / 60.0
            gallons += r["flow"] * dt
    return gallons
