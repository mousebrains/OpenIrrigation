<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>POC Flow editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'pocFlow';
$fields = ['poc', 'sensor', 'name', 'make', 'model', 'toHertz', 'K', 'offset'];

if (!empty($_POST)) {postUp($_POST, $table, $fields, $parDB);}

function myForm(array $row, array $poc, array $sensors, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	selectFromList('POC', 'poc', $poc, $row['poc']);
	selectFromList('Sensor', 'sensor', $sensors, $row['sensor']);
	inputRow('Name', 'name', $row['name'], 'text', 'Sensor Name', true);
	inputRow('Make', 'make', $row['make'], 'text', 'Tucor');
	inputRow('Model', 'model', $row['model'], 'text', 'TDI');
	inputRow('Hertz/reading', 'toHertz', $row['toHertz'], 
			'number', '0.5', false, 0.01, 0, 10);
	inputRow('K value', 'K', $row['K'], 
			'number', '0.123', false, 0.0001, 0, 10);
	inputRow('offset value', 'offset', $row['offset'], 
			'number', '0.123', false, 0.0001, 0, 10);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$poc = $parDB->loadTable('poc', 'id', 'name', 'name');
$sensors = $parDB->loadTable('sensor', 'id', 'name', 'addr');

$results = $parDB->query("SELECT * FROM $table ORDER BY name;");
while ($row = $results->fetchArray()) {
	myForm($row, $poc, $sensors, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'','poc'=>key($poc),'sensor'=>key($sensors)]),
       $poc, $sensors, 'Create');
?>
</body>
</html>
