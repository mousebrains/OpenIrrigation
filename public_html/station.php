<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Station editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'station';
$fields = ['poc', 'sensor', 'name', 'station', 'make', 'model', 
	'sortOrder', 'cycleTime', 'soakTime', 
	'measuredFlow', 'userFlow', 'lowFlowFrac', 'highFlowFrac', 
	'onDelay', 'offDelay'];

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
	inputRow('Station', 'station', $row['station'], 'number', '1', true, 1, 1, 200);
	inputRow('Make', 'make', $row['make'], 'text', 'Tucor');
	inputRow('Model', 'model', $row['model'], 'text', 'TDI');
	inputRow('Sort Order', 'sortOrder', $row['sortOrder'], 'number', '1', false, 1, 1, 200);
	inputRow('Maximum Cycle Time (s)', 'cycleTime', $row['cycleTime'], 'number', '1', false, 1, 60, 100000);
	inputRow('Minimum Soak Time (s)', 'soakTime', $row['soakTime'], 'number', '1', false, 1, 60, 100000);
	inputRow('On Delay (s)', 'onDelay', $row['onDelay'], 'number', '1', false, 1, 1, 900);
	inputRow('Off Delay (s)', 'offDelay', $row['offDelay'], 'number', '1', false, 1, 1, 900);
	inputRow('Measured Flow (GPM)', 'measuredFlow', $row['measuredFlow'], 
			'number', '5.1', false, 0.01, 0, 100);
	inputRow('User Flow (GPM)', 'userFlow', $row['userFlow'], 
			'number', '5.1', false, 0.01, 0, 100);
	inputRow('Low flow fraction', 'lowFlowFrac', $row['lowFlowFrac'], 
			'number', '0.1', false, 0.1, 0, 10);
	inputRow('High flow fraction', 'highFlowFrac', $row['highFlowFrac'], 
			'number', '0.1', false, 0.1, 0, 10);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$poc = $parDB->loadTable('poc', 'id', 'name', 'name');
$sensors = $parDB->loadTable('sensor', 'id', 'name', 'addr');

$results = $parDB->query("SELECT * FROM $table ORDER BY sortOrder;");
while ($row = $results->fetchArray()) {
	myForm($row, $poc, $sensors, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'','poc'=>key($poc),'sensor'=>key($sensors)]), 
       $poc, $sensors, 'Create');
?>
</body>
</html>
