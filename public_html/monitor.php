<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='icon' href='/favicon.png' sizes="32x32">
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<script src="js/irrigation.js"></script>
<title>Wild Iris Irrigation</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
?>
<div>
<table>
<tbody id='topActions'>
<th><form id='clearAll'><input type='submit' value='Clear All'></form></th>
<th><form id='allOff'><input type='submit' value='All Off'></form></th>
</tbody>
</table>
</div>
<div id='activeDiv' style='display:none;'>
<center>
<table id='activeTable'>
<caption>Active stations</caption>
<thead><tr><th></th><th>Station</th><th>Start</th><th>Run Time</th><th>Time Left</th>
<th>Program</th><th>Pre</th><th>Peak</th><th>Post</th><th>On Code</th></tr></thead>
<tbody></tbody>
<tfoot><tr><th></th><th>Station</th><th>Start</th><th>Run Time</th><th>Time Left</th>
<th>Program</th><th>Pre</th><th>Peak</th><th>Post</th><th>On Code</th></tr></tfoot>
</table>
</center>
<hr>
</div>
<div id='pendingDiv' style='display:none;'>
<center>
<table id='pendingTable'>
<caption>Pending stations</caption>
<thead><tr><th></th><th>Station</th><th>Start</th><th>Run Time</th><th>Program</th></tr></thead>
<tbody></tbody>
<tfoot><tr><th></th><th>Station</th><th>Start</th><th>Run Time</th><th>Program</th></tr></tfoot>
</table>
</center>
<hr>
</div>
<div id='pastDiv' style='display:none;'>
<center>
<table id='pastTable'>
<caption>Historical stations</caption>
<thead><tr><th>Station</th><th>Start</th><th>Run Time</th><th>Time Left</th>
<th>Program</th><th>Pre</th><th>Peak</th><th>Post</th><th>On Code</th></tr></thead>
<tbody></tbody>
<tfoot><tr><th>Station</th><th>Start</th><th>Run Time</th><th>Time Left</th>
<th>Program</th><th>Pre</th><th>Peak</th><th>Post</th><th>On Code</th></tr></tfoot>
</table>
</center>
</div>
<script src=js/monitor.js></script>
</body>
</html> 
