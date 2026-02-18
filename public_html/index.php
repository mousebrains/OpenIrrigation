<?php require_once 'php/version.php'; ?>
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='icon' href='/favicon.png' sizes="32x32">
<link rel='stylesheet' type='text/css' href='css/irrigation.css?v=<?php echo OI_ASSET_VERSION; ?>'>
<script defer src="js/jquery.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/irrigation.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<title>Wild Iris Irrigation</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
?>
<div class='table-wrap'>
<table id='stnTable'>
<thead><tr><th>Station</th><th>Minutes</th></tr></thead>
<tbody></tbody>
<tfoot><tr><th>Station</th><th>Minutes</th></tr></tfoot>
</table>
</div>
<br>
<span id='pocBlock' style='display:none'>
<div class='table-wrap'>
<table id='pocTable'>
<caption>Point(s) of connection</caption>
<thead><tr><th>Master Valve</th><th>Minutes</th></tr></thead>
<tbody></tbody>
<tfoot><tr><th>Master Valve</th><th>Minutes</th></tr></tfoot>
</table>
</div>
</span>
<script defer src="js/index.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
</body>
</html>
