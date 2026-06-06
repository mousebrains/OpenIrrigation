<?php
require_once 'php/DB1.php';
$db = DB::getInstance();
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
	echo $db->mkMsg(false, 'POST required');
	exit;
}

$hours = isset($_POST['hours']) ? $_POST['hours'] : 24;
if (!is_numeric($hours)) {
	echo $db->mkMsg(false, 'Invalid hours parameter');
	exit;
}
$hours = max(1, min(72, (int)$hours));
$buckets = min($hours * 60, 500);

if (!$db->isConnected()) {
	echo json_encode(['error' => 'Database connection failed']);
	exit;
}

// Downsample by keeping the last actual reading in each bucket. Flow is a
// step signal, so averaging within a bucket fabricates values that never
// existed (e.g. a run-end 0 averaged with a real reading); the last reading
// preserves true (timestamp, flow) pairs and run-end zeros always survive.
// cumVol integrates the raw step signal (GPM * minutes -> gallons) before
// downsampling, resetting at each local midnight; the scan starts at
// midnight of the window-start day so a partial first day still shows the
// correct since-midnight total.
$flow = $db->loadRowsNum(
	"WITH raw AS ("
	. "  SELECT timestamp, flow,"
	. "   lag(timestamp) OVER (ORDER BY timestamp) AS prevTS,"
	. "   lag(flow) OVER (ORDER BY timestamp) AS prevFlow"
	. "  FROM sensorLog"
	. "  WHERE timestamp >= date_trunc('day', NOW() - INTERVAL '1 hour' * ?)"
	. " ), vol AS ("
	. "  SELECT timestamp, flow,"
	. "   SUM(COALESCE(prevFlow, 0)"
	. "    * EXTRACT(EPOCH FROM timestamp - GREATEST(prevTS, date_trunc('day', timestamp)))"
	. "    / 60) OVER (PARTITION BY date_trunc('day', timestamp) ORDER BY timestamp) AS cumVol"
	. "  FROM raw"
	. " )"
	. " SELECT ROUND(EXTRACT(EPOCH FROM timestamp)) AS t,"
	. " ROUND(flow::numeric, 2) AS flow,"
	. " ROUND(cumVol::numeric, 1) AS vol"
	. " FROM ("
	. "  SELECT DISTINCT ON (bucket) timestamp, flow, cumVol"
	. "  FROM ("
	. "   SELECT timestamp, flow, cumVol, width_bucket("
	. "     EXTRACT(EPOCH FROM timestamp),"
	. "     EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour' * ?),"
	. "     EXTRACT(EPOCH FROM NOW()),"
	. "     ?"
	. "   ) AS bucket"
	. "   FROM vol"
	. "   WHERE timestamp >= NOW() - INTERVAL '1 hour' * ?"
	. "  ) bucketed"
	. "  ORDER BY bucket, timestamp DESC"
	. " ) sub"
	. " ORDER BY t",
	[$hours, $hours, $buckets, $hours]
);

$stations = $db->loadRowsNum(
	"SELECT s.name,"
	. " ROUND(EXTRACT(EPOCH FROM tOn)) AS tOn,"
	. " ROUND(EXTRACT(EPOCH FROM tOff)) AS tOff"
	. " FROM action a"
	. "  JOIN sensor sen ON a.sensor = sen.id"
	. "  JOIN station s ON s.sensor = sen.id"
	. " WHERE a.tOff >= NOW() - INTERVAL '1 hour' * ? AND a.tOn <= NOW()"
	. " UNION ALL"
	. " SELECT s.name,"
	. " ROUND(EXTRACT(EPOCH FROM tOn)) AS tOn,"
	. " ROUND(EXTRACT(EPOCH FROM tOff)) AS tOff"
	. " FROM historical h"
	. "  JOIN sensor sen ON h.sensor = sen.id"
	. "  JOIN station s ON s.sensor = sen.id"
	. " WHERE h.tOff >= NOW() - INTERVAL '1 hour' * ? AND h.tOn <= NOW()"
	. " ORDER BY tOn",
	[$hours, $hours]
);

$result = ['flow' => $flow, 'stations' => $stations];
if ($db->getError()) {
	$result['error'] = 'Query error: ' . $db->getError();
}
echo json_encode($result);
