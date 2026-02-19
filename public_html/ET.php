<?php require_once 'php/version.php'; ?>
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='icon' type='image/png' href='/favicon.png' sizes='32x32'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css?v=<?php echo OI_ASSET_VERSION; ?>'>
<style>
.chart-container {
	position: relative;
	width: 80%;
	max-height: 75vh;
	margin: 0 auto;
}
.et-controls {
	text-align: center;
	padding: 10px;
}
</style>
<script defer src="js/jquery.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/irrigation.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/chart.umd.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/chartjs-adapter-date-fns.bundle.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/et.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<title>ET Data</title>
</head>
<body>
<?php require_once 'php/navBar.php'; ?>
<div class='et-controls'>
<label for='et-select'>Parameter:</label>
<select id='et-select'>
<?php
require_once 'php/DB1.php';
if (!$db->isConnected()) {
	echo "<option value=''>Database error</option>";
} else {
	$a = $db->loadRows(
		"SELECT p.id, p.val FROM params p"
		. " WHERE p.grp='ET'"
		. " AND EXISTS (SELECT 1 FROM ETannual WHERE code = p.id)"
		. " ORDER BY p.val;", []);
	if (empty($a) && $db->getError()) {
		echo "<option value=''>Query error</option>";
	} else {
		foreach ($a as $item) {
			$id = $item['id'];
			$val = htmlspecialchars($item['val'], ENT_QUOTES, 'UTF-8');
			$sel = ($item['val'] === 'ET (in/day)') ? ' selected' : '';
			echo "<option value='$id'$sel>$val</option>";
		}
	}
}
?>
</select>
</div>
<div class='chart-container'>
 <canvas id='etChart'></canvas>
</div>
</body>
</html>
