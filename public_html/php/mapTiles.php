<?php
// The aerial imagery tiles fetchMapTiles.py caches for map.php, in OI_TILEDIR:
// TILEDIR/<layer>/<z>/<x>/<y>.jpg and TILEDIR/<layer>/layer.json

// OI_TILEDIR is in config.php, which make generates from config.php.in
function oiTileDir(): string {
	require_once __DIR__ . '/config.php';
	$dir = defined('OI_TILEDIR') ? constant('OI_TILEDIR') : '';
	return is_string($dir) ? rtrim($dir, '/') : '';
}

// A layer id is a directory name fetchMapTiles.py accepts: letters, digits, - and _
function oiTileLayerOK(string $id): bool {
	return preg_match('/^[A-Za-z0-9_-]{1,40}$/', $id) === 1;
}

/**
 * The cached layers, newest imagery first, from each layer's layer.json
 * @return list<array{id: string, label: string, attribution: string, bounds: mixed,
 *   minZoom: int, maxNativeZoom: int, fetched: string}>
 */
function oiTileLayers(): array {
	$dir = oiTileDir();
	if ($dir === '' || !is_dir($dir)) return [];
	$layers = [];
	foreach (glob($dir . '/*/layer.json') ?: [] as $fn) {
		$id = basename(dirname($fn));
		if (!oiTileLayerOK($id)) continue;
		$txt = file_get_contents($fn);
		$meta = is_string($txt) ? json_decode($txt, true) : null;
		if (!is_array($meta)) continue;
		$layers[] = [
			'id' => $id,
			'label' => is_string($meta['label'] ?? null) ? $meta['label'] : $id,
			'attribution' => is_string($meta['attribution'] ?? null) ? $meta['attribution'] : '',
			'bounds' => $meta['bounds'] ?? null,
			'minZoom' => is_int($meta['minZoom'] ?? null) ? $meta['minZoom'] : 0,
			'maxNativeZoom' => is_int($meta['maxNativeZoom'] ?? null) ? $meta['maxNativeZoom'] : 20,
			'fetched' => is_string($meta['fetched'] ?? null) ? $meta['fetched'] : '',
		];
	}
	usort($layers, fn(array $a, array $b): int => strcmp($b['id'], $a['id'])); // osip2024 before osip2022
	return $layers;
}
