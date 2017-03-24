<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>POC Pump editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

if (!empty($_POST)) {
	$table = 'pocPump';
	if (!empty($_POST['delete'])) { // Delete the entry
		$parDB->deleteFromTable($table, 'id', $_POST['id']);
	} else {
		$fields = ['poc', 'sensor', 'name', 'make', 'model', 
			'minFlow', 'maxFlow', 'delayOn', 'delayOff', 'priority'];
		if ($_POST['id'] == '') {
			$parDB->insertIntoTable($table, $fields, $_POST);	
		} else {
			$parDB->maybeUpdate($table, $fields, $_POST);	
		}
	}
}

function myForm(array $row, array $poc, array $sensors, string $submit) {
	$NONC = [0 => 'Normally Closed', 1 => 'Normally Open'];
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
	inputRow('Minimum Flow (GPM)', 'minFlow', $row['minFlow'], 'number', '0.1', false, 
		0.1, 0, 1000);
	inputRow('Maximum Flow (GPM)', 'maxFlow', $row['maxFlow'], 'number', '100', false, 
		0.1, 0, 1000);
	inputRow('On Delay (s)', 'delayOn', $row['delayOn'], 'number', '100', false, 
		1, 0, 3600);
	inputRow('Off Delay (s)', 'delayOff', $row['delayOff'], 'number', '100', false, 
		1, 0, 3600);
	inputRow('Priority 0=highest', 'priority', $row['priority'], 'number', '1', false, 
		1, 0, 100);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$poc = $parDB->loadTable('poc', 'id', 'name', 'name');
$sensors = $parDB->loadTable('sensor', 'id', 'name', 'addr');

$blankRow = ['id'=>'', 'poc'=>'', 'sensor'=>'', 'name'=>'', 'make'=>'', 'model'=>'',
	'minFlow'=>'', 'maxFlow'=>'', 'delayOn'=>'', 'delayOff'=>'', 'priority'=>''];
$results = $parDB->query('SELECT * FROM pocPump ORDER BY name;');
while ($row = $results->fetchArray()) {
	foreach ($row as $key => $value) {$blankRow[$key] = '';}
	myForm($row, $poc, $sensors, 'Update');
}

myForm($blankRow, $poc, $sensors, 'Create');
?>
</body>
</html>
