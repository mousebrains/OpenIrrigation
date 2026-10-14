<?php
// One cached aerial imagery tile for map.js,
// e.g. mapTile.php?layer=osip2024&z=19&x=83011&y=188536
// Read-only and database-free: it only reads files fetchMapTiles.py wrote.
require_once 'php/mapTiles.php';

function mapNotFound(): never {
	http_response_code(404);
	exit();
}

$layer = $_GET['layer'] ?? '';
if (!is_string($layer) || !oiTileLayerOK($layer)) mapNotFound();
$zxy = [];
foreach (['z', 'x', 'y'] as $key) {
	$val = $_GET[$key] ?? '';
	if (!is_string($val) || !ctype_digit($val) || strlen($val) > 8) mapNotFound();
	$zxy[] = (int)$val;
}
[$z, $x, $y] = $zxy;
if ($z > 22 || $x >= (1 << $z) || $y >= (1 << $z)) mapNotFound();

$dir = oiTileDir();
$fn = "$dir/$layer/$z/$x/$y.jpg";
$size = ($dir === '') ? false : @filesize($fn);
if ($size === false) mapNotFound(); // outside the cached area, or no tiles yet

header('Content-Type: image/jpeg');
header('Content-Length: ' . $size);
header('Cache-Control: public, max-age=604800'); // a week; refetched imagery shows within that
readfile($fn);
