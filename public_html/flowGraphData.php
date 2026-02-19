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

$flow = $db->loadRowsNum(
	"SELECT"
	. " ROUND(EXTRACT(EPOCH FROM MIN(timestamp))) AS t,"
	. " ROUND(AVG(flow)::numeric, 2) AS flow"
	. " FROM sensorLog"
	. " WHERE timestamp >= NOW() - INTERVAL '1 hour' * ?"
	. " GROUP BY width_bucket("
	. "   EXTRACT(EPOCH FROM timestamp),"
	. "   EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour' * ?),"
	. "   EXTRACT(EPOCH FROM NOW()),"
	. "   ?"
	. " )"
	. " ORDER BY t",
	[$hours, $hours, $buckets]
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
