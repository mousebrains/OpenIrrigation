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
<title>Process Status</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
?>
<center>
<table>
<thead><tr><th>Item</th><th>Date</th><th>Message</th></tr></thead>
<tbody id='messages'></tbody>
<tfoot><tr><th>Item</th><th>Date</th><th>Message</th></tr></tfoot>
</table></center>
<script src=js/processState.js></script>
</body>
</html> 
