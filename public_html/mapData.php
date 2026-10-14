<?php
// The site map for map.js: the map features, the valves in each box with
// their stations' programs and last/next/current runs, and the cached
// imagery layers.  Read-only: nothing here writes the database.
header('Content-Type: application/json');

/** @param array<string, mixed> $data */
function mapReply(array $data): never {
	$json = json_encode($data);
	exit($json === false ? '{"success":false,"message":"Unable to encode the map"}' : $json);
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
	http_response_code(405);
	header('Allow: POST');
	mapReply(['success' => false, 'message' => 'POST required']);
}

require_once 'php/DB1.php';
require_once 'php/mapTiles.php';
$db = DB::getInstance();

function mapFloat(mixed $v): ?float { return is_numeric($v) ? (float)$v : null; }
function mapInt(mixed $v): ?int { return is_numeric($v) ? (int)$v : null; }
function mapStr(mixed $v): ?string { return is_string($v) ? $v : null; }
function mapBool(mixed $v): bool { return in_array($v, [true, 1, '1', 't', 'true'], true); }

try {
	$features = $db->loadRows(
		"SELECT f.id, f.name, w.key AS kind, w.label AS kindlabel,"
		. " f.latitude, f.longitude, f.notes"
		. " FROM mapFeature f LEFT JOIN webList w ON w.id=f.kind"
		. " ORDER BY f.name;", []);
	// Programs, except the manual one, marked "(off)" when the station's mode or the
	// program is off; times are epoch seconds
	$valves = $db->loadRows(
		"SELECT s.mapFeature AS feature, s.addr, d.key AS devtype, s.name AS sensor,"
		. " s.mapPosition AS position, st.name AS station,"
		. " (SELECT string_agg(DISTINCT p.name"
		. "     || CASE WHEN m.key='off' OR o.key='off' THEN ' (off)' ELSE '' END, ', ')"
		. "   FROM pgmStn g JOIN program p ON p.id=g.program"
		. "   LEFT JOIN webList m ON m.id=g.mode LEFT JOIN webList o ON o.id=p.onOff"
		. "   WHERE g.station=st.id AND NOT COALESCE(p.qManual, False)) AS programs,"
		. " (SELECT ROUND(EXTRACT(EPOCH FROM max(h.tOff))) FROM historical h"
		. "   WHERE h.sensor=s.id) AS lastrun,"
		. " (SELECT ROUND(EXTRACT(EPOCH FROM min(a.tOn))) FROM action a"
		. "   WHERE a.sensor=s.id AND a.cmd=0 AND a.cmdOn IS NOT NULL AND a.tOn > now()) AS nextrun,"
		. " EXISTS (SELECT 1 FROM active a WHERE a.sensor=s.id) AS onnow"
		. " FROM sensor s"
		. " LEFT JOIN station st ON st.sensor=s.id"
		. " LEFT JOIN webList d ON d.id=s.devType"
		. " WHERE s.mapFeature IS NOT NULL"
		. " ORDER BY s.mapFeature, s.mapOrder NULLS LAST, s.addr;", []);
	$sites = $db->loadRows(
		"SELECT name, latitude, longitude FROM site"
		. " WHERE latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY id LIMIT 1;", []);
} catch (PDOException $e) {
	error_log('mapData.php: ' . $e->getMessage());
	mapReply(['success' => false, 'message' => 'Unable to load the map from the database']);
}

mapReply([
	'success' => true,
	'now' => time(),
	'site' => empty($sites) ? null : [
		'name' => mapStr($sites[0]['name']),
		'latitude' => mapFloat($sites[0]['latitude']),
		'longitude' => mapFloat($sites[0]['longitude']),
	],
	'features' => array_map(fn(array $f): array => [
		'id' => mapInt($f['id']),
		'name' => mapStr($f['name']),
		'kind' => mapStr($f['kind']) ?? 'other',
		'kindLabel' => mapStr($f['kindlabel']) ?? 'Other',
		'latitude' => mapFloat($f['latitude']),
		'longitude' => mapFloat($f['longitude']),
		'notes' => mapStr($f['notes']),
	], $features),
	'valves' => array_map(fn(array $v): array => [
		'feature' => mapInt($v['feature']),
		'addr' => mapInt($v['addr']),
		'devType' => mapStr($v['devtype']),
		'sensor' => mapStr($v['sensor']),
		'position' => mapStr($v['position']),
		'station' => mapStr($v['station']),
		'programs' => mapStr($v['programs']),
		'lastRun' => mapInt($v['lastrun']),
		'nextRun' => mapInt($v['nextrun']),
		'onNow' => mapBool($v['onnow']),
	], $valves),
	'layers' => oiTileLayers(),
]);
