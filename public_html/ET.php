<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='icon' href='/favicon.png' sizes="32x32">
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<style>
* { box-sizing: border-box; }
.row {display: flex;}
.column {
	padding: 10px;
	height: 300px; /* For demo only */
}
.left {flex: 70%;}
.right {flex: 30%;}
</style>
<script src="js/jquery.min.js"></script>
<script src="js/irrigation.js"></script>
<script src="js/et.js"></script>
<title>probar</title>
</head>
<body>
<div class = 'row'>
<div class='column left' id='leftCol'>
<table id='tblData'>
<colgroup id='colGrp'>
  <col id='colDate'>
</colgroup>
<thead><th>Date</th></thead>
<tbody></tbody>
<tfoot><th>Date</th></tfoot>
</table>
</div>
<div class='column right' id='rightCol'>
<form>
<table>
<thead><th>Daily</th><th>Description</th><th>Annual</th></thead>
<tbody>
<?php
require_once 'php/DB1.php';
$a = $db->loadRows("SELECT id,val FROM params WHERE grp='ET' ORDER BY val;", []);
foreach ($a as $item) {
	$id = $item['id'];
	$val = $item['val'];
	echo "<tr>"
		. "<td><input type='checkbox' id='d$id' onclick='dailyClick($id)'></td>"
		. "<th>" . htmlspecialchars($val, ENT_QUOTES, 'UTF-8') . "</th>"
		. "<td><input type='checkbox' id='y$id' onclick='yearlyClick($id)'></td>"
		. "</tr>";
}
?>
</tbody>
<tfoot><th>Daily</th><th>Description</th><th>Annual</th></tfoot>
</table>
</form>
</div>
</div>
</body>
</html>
