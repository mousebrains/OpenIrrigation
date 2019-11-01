<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Wild Iris Irrigation</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
?>
<center>
<table id='stnTable'>
<thead><tr><th>Station</th><th>Minutes</th></tr></thead>
<tbody></tbody>
<tfoot><tr><th>Station</th><th>Minutes</th></tr></tfoot>
</table>
</center>
<br>
<span id='pocBlock' style='display:none'>
<center>
<table id='pocTable'>
<caption>Point(s) of connection</caption>
<thead><tr><th>Master Valve</th><th>Minutes</th></tr></thead>
<tbody></tbody>
<tfoot><tr><th>Master Valve</th><th>Minutes</th></tr></tfoot>
</table>
</center>
</span>
<script src=js/index.js></script>
</body>
</html> 
