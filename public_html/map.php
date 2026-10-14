<?php require_once 'php/version.php'; ?>
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='icon' type='image/png' href='/favicon.png' sizes='32x32'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css?v=<?php echo OI_ASSET_VERSION; ?>'>
<link rel='stylesheet' type='text/css' href='css/leaflet.css?v=<?php echo OI_ASSET_VERSION; ?>'>
<style>
html, body { height: 100%; }
body { display: flex; flex-direction: column; }
#map { flex: 1 1 auto; min-height: 300px; }
/* Feature icons, by mapFeature kind (webList grp='mapKind') */
.oi-map-icon { box-sizing: border-box; width: 14px; height: 14px; border: 2px solid #fff;
	box-shadow: 0 0 3px #000; border-radius: 50%; background: #888; }
.oi-map-icon.valveBox { width: 20px; height: 20px; border-radius: 3px; background: #1a9e1a; }
.oi-map-icon.valveBox.on { background: #1e6bff; animation: oi-map-pulse 1.2s ease-in-out infinite; }
.oi-map-icon.equipment { width: 18px; height: 18px; border-radius: 3px; background: #e0b000; }
.oi-map-icon.shutoff { background: #d00000; }
.oi-map-icon.backflow { background: #9040ff; border-radius: 2px; transform: rotate(45deg); }
.oi-map-icon.drain { background: #00a0ff; }
.oi-map-icon.hoseBib { width: 12px; height: 12px; background: #fff; border-color: #0080c0; }
@keyframes oi-map-pulse { 50% { box-shadow: 0 0 10px 4px #1e6bff; } }
.oi-map-legend { background: #fff; padding: 4px 8px; border-radius: 4px; line-height: 20px; }
.oi-map-legend .oi-map-icon { display: inline-block; vertical-align: middle; margin-right: 6px; }
.oi-map-popup h3 { margin: 0 0 4px 0; font-size: 110%; }
.oi-map-popup .kind { color: #666; }
.oi-map-popup .notes { margin: 4px 0; white-space: pre-line; }
.oi-map-popup table { font-size: 90%; margin-top: 4px; }
.oi-map-popup th, .oi-map-popup td { padding: 2px 5px; text-align: left; }
.oi-map-popup td.label { text-align: right; font-weight: bold; }
.oi-map-popup tr.on td { background: #dbe8ff; font-weight: bold; }
.oi-map-message { background: #fff; padding: 4px 8px; border-radius: 4px; max-width: 320px; }
</style>
<script defer src="js/jquery.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/irrigation.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/leaflet.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<title>Site Map</title>
</head>
<body>
<?php require_once 'php/navBar.php'; ?>
<div id='map'></div>
<script defer src="js/map.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
</body>
</html>
