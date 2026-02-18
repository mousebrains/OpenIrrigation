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
.hour-buttons { margin: 10px 0; }
.hour-buttons button {
	padding: 6px 14px;
	margin: 0 4px;
	cursor: pointer;
	border: 1px solid #ccc;
	background: #f0f0f0;
	border-radius: 4px;
}
.hour-buttons button.active {
	background: #337ab7;
	color: #fff;
	border-color: #337ab7;
}
.chart-container {
	position: relative;
	width: 100%;
	max-width: 1200px;
	margin: 0 auto;
}
</style>
<script defer src="js/jquery.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/irrigation.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/chart.umd.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/chartjs-adapter-date-fns.bundle.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<title>Flow Graph</title>
</head>
<body>
<?php require_once 'php/navBar.php'; ?>
<div class='hour-buttons'>
 <button data-hours='1'>1h</button>
 <button data-hours='2'>2h</button>
 <button data-hours='6'>6h</button>
 <button data-hours='12'>12h</button>
 <button data-hours='24' class='active'>24h</button>
 <button data-hours='48'>48h</button>
 <button data-hours='72'>72h</button>
</div>
<div class='chart-container'>
 <canvas id='flowChart'></canvas>
</div>
<script defer src="js/flowGraph.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
</body>
</html>
