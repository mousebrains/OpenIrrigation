<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Sensor editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'sensor';
$fields = ['controller', 'name', 'latitude', 'longitude', 'passiveCurrent',
	'activeCurrent', 'devType', 'driver', 'addr', 'make', 'model', 
	'installed', 'notes'];

if (!empty($_POST)) {
	if (!empty($_POST['delete'])) { // Delete the entry
		$parDB->deleteFromTable($table, 'id', $_POST['id']);
	} else {
		$_POST['installed'] = strtotime($_POST['installed']);
		$_POST['oldinstalled'] = strtotime($_POST['oldinstalled']);
		if ($_POST['id'] == '') {
			$parDB->insertIntoTable($table, $fields, $_POST);	
		} else {
			$parDB->maybeUpdate($table, $fields, $_POST);	
		}
	}
}

function myForm(array $row, array $controllers, array $devTypes, string $submit) {
	$row['installed'] = date('Y-m-d', intval($row['installed']));
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	selectFromList('Controller', 'controller', $controllers, $row['controller']);
	inputRow('Name', 'name', $row['name'], 'text', 'Sensor Name', true);
	inputRow('Latitude (deg)', 'latitude', $row['latitude'], 'latlon', '-45.6');
	inputRow('Longitude (deg)', 'longitude', $row['longitude'], 'latlon', '-45.6');
	inputRow('Passive Current (mAmps)', 'passiveCurrent', $row['passiveCurrent'], 
			'number', '0.5', false, 0.5, 0, 100);
	inputRow('Active Current (mAmps)', 'activeCurrent', $row['activeCurrent'], 
			'number', '0.5', false, 0.5, 0, 100);
	selectFromList('Device Type', 'devType', $devTypes, $row['devType']);
	inputRow('Device Driver', 'driver', $row['driver'], 'text', 'TDI');
	inputRow('Device Address', 'addr', $row['addr'], 'number', '0');
	inputRow('Make', 'make', $row['make'], 'text', 'Tucor');
	inputRow('Model', 'model', $row['model'], 'text', 'TDI');
	inputRow('Installed', 'installed', $row['installed'], 'date');
	inputRow('Notes', 'notes', $row['notes'], 'text', 'something intersting');
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$controllers = $parDB->loadTable('controller', 'id', 'name', 'name');
$devTypes = $parDB->loadTable('sensorDevType', 'id', 'label', 'label');

$results = $parDB->query("SELECT * FROM $table ORDER BY name;");
while ($row = $results->fetchArray()) {
	myForm($row, $controllers, $devTypes, 'Update');
}

$blankRow = array_fill_keys($fields, '');
$blankRow['id'] = '';
myForm($blankRow, $controllers, $devTypes, 'Create');
?>
</body>
</html>
