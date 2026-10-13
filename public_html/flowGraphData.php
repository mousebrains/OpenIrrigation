<?php
// Flow and cumulative volume for flowGraph.js. Read-only: nothing here
// writes the database, not even changeLog for a bad request.
header('Content-Type: application/json');

function reply(bool $flag, string $msg): never {
	exit(json_encode(['success' => $flag, 'message' => $msg]));
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
	http_response_code(405);
	header('Allow: POST');
	reply(false, 'POST required');
}

$hours = $_POST['hours'] ?? '24';
if (!is_string($hours) || !is_numeric($hours)) reply(false, 'Invalid hours parameter');
$hours = max(1, min(72, (int)$hours));
$buckets = min($hours * 60, 500);

require_once 'php/DB1.php';
$db = DB::getInstance();

try {
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

	// The midnights where the volume above resets, so the browser draws the
	// resets where the database put them: its time zone, not the browser's
	$midnights = $db->loadRowsNum(
		"SELECT ROUND(EXTRACT(EPOCH FROM d)) FROM generate_series("
		. " date_trunc('day', NOW() - INTERVAL '1 hour' * ?) + INTERVAL '1 day',"
		. " NOW(), INTERVAL '1 day') AS d",
		[$hours]
	);
} catch (PDOException $e) {
	error_log("flowGraphData: " . $e->getMessage());
	reply(false, 'Database error: ' . DB::pgMessage($e)[0]);
}

echo json_encode(['flow' => $flow, 'stations' => $stations,
	'midnights' => array_column($midnights, 0)]);
