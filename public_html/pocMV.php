<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>POC Master Valve editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'pocMV';
$fields = ['poc', 'sensor', 'name', 'make', 'model', 'qNormallyOpen'];

if (!empty($_POST)) {$parDB->postUp($table, $fields, $_POST);}

function myForm(array $row, array $poc, array $sensors, string $submit) {
	$NONC = [0 => 'Normally Closed', 1 => 'Normally Open'];
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	selectFromList('POC', 'poc', $poc, $row['poc']);
	selectFromList('Sensor', 'sensor', $sensors, $row['sensor']);
	inputRow('Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Sensor Name', 'required'=>NULL]);
	inputRow('Make', 'make', $row['make'], 'text', ['placeholder'=>'Tucor']);
	inputRow('Model', 'model', $row['model'], 'text', ['placeholder'=>'TDI']);
	selectFromList('Normally open/closed', 'qNormallyOpen', $NONC, $row['qNormallyOpen']);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$poc = $parDB->loadTable('poc', 'id', 'name', 'name');
$sensors = $parDB->loadTable('sensor', 'id', 'name', 'addr');

$results = $parDB->query("SELECT * FROM $table ORDER BY name COLLATE NOCASE;");
while ($row = $results->fetchArray()) {
	myForm($row, $poc, $sensors, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'','poc'=>key($poc),'sensor'=>key($sensors)]), 
       $poc, $sensors, 'Create');
?>
</body>
</html>
