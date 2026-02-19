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
.et-row { display: flex; }
.et-chart { flex: 70%; padding: 10px; }
.et-params { flex: 30%; padding: 10px; }
.chart-container {
	position: relative;
	width: 100%;
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
<div class='et-row'>
<div class='et-chart'>
 <div class='chart-container'>
  <canvas id='etChart'></canvas>
 </div>
</div>
<div class='et-params'>
<form>
<table>
<thead><tr><th>Daily</th><th>Description</th><th>Annual</th></tr></thead>
<tbody>
<?php
require_once 'php/DB1.php';
$a = $db->loadRows("SELECT id,val FROM params WHERE grp='ET' ORDER BY val;", []);
foreach ($a as $item) {
	$id = $item['id'];
	$val = $item['val'];
	echo "<tr>"
		. "<td><input type='checkbox' class='et-daily' data-codigo='$id'></td>"
		. "<th>" . htmlspecialchars($val, ENT_QUOTES, 'UTF-8') . "</th>"
		. "<td><input type='checkbox' class='et-annual' data-codigo='$id'></td>"
		. "</tr>";
}
?>
</tbody>
<tfoot><tr><th>Daily</th><th>Description</th><th>Annual</th></tr></tfoot>
</table>
</form>
</div>
</div>
</body>
</html>
