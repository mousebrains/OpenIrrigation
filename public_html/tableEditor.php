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
<title>Parameter Editor</title>
</head>
<body>
<?php
if (empty($_GET['tbl'])) {exit("<h1>tbl parameter not supplied</h1>\n</body>\n</html>\n");}

require_once 'php/DB1.php';
$tbl = $_GET['tbl'];
if (!$db->tableExists($tbl)) {exit("<h1>Table, $tbl, does not exist</h1>\n</body>\n</html>\n");}
echo '<script>var myTableName="' . $tbl . '";</script>';

require_once 'php/navBar.php';
?>
<center>
<table>
<thead></thead>
<tbody></tbody>
<tfoot></tfoot>
</table>
<form action='javascript:void(0);'>
<input type='button' value='Batch Update' id='batchUpdate'>
<input type='button' value='Cancel' id='batchCancel'>
</form>
</center>
<script src=js/tableEditor.js>
</script>
</body>
</html> 
