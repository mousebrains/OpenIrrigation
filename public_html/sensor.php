<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
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

$adjust = ['installed'=>'date'];

if (!empty($_POST)) {$parDB->postUp($table, $fields, $_POST, $adjust);}

function myForm(array $row, array $controllers, array $devTypes, string $submit) {
	global $parDB;
	global $adjust;
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	selectFromList('Controller', 'controller', $controllers, $row['controller']);
	inputRow('Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Sensor Name', 'required'=>NULL]);
	inputRow('Latitude (deg)', 'latitude', $row['latitude'], 'latlon', 
		['placeholder'=>-45.6]);
	inputRow('Longitude (deg)', 'longitude', $row['longitude'], 'latlon', 
		['placeholder'=>-145.6]);
	inputRow('Passive Current (mAmps)', 'passiveCurrent', $row['passiveCurrent'], 'number', 
		['placeholder'=>0.5, 'step'=>0.5, 'min'=>0, 'max'=>100]);
	inputRow('Active Current (mAmps)', 'activeCurrent', $row['activeCurrent'], 'number', 
		['placeholder'=>0.5, 'step'=>0.5, 'min'=>0, 'max'=>100]);
	selectFromList('Device Type', 'devType', $devTypes, $row['devType']);
	inputRow('Device Driver', 'driver', $row['driver'], 'text', ['placeholder'=>'TDI']);
	inputRow('Device Address', 'addr', $row['addr'], 'number', ['placeholder'=>0]);
	inputRow('Make', 'make', $row['make'], 'text', ['placeholder'=>'Tucor']);
	inputRow('Model', 'model', $row['model'], 'text', ['placeholder'=>'TDI']);
	inputRow('Installed', 'installed', 
		$parDB->unadjust('installed',$row['installed'], $adjust), 'date');
	inputRow('Notes', 'notes', $row['notes'], 'text', ['placeholder'=>'something intersting']);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$controllers = $parDB->loadTable('controller', 'id', 'name', 'name');
$devTypes = $parDB->loadTable('sensorDevType', 'id', 'label', 'label');

$results = $parDB->query("SELECT * FROM $table ORDER BY addr;");
while ($row = $results->fetchArray()) {
	myForm($row, $controllers, $devTypes, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'','controller'=>key($controllers),'devType'=>key($devTypes)]), 
	$controllers, $devTypes, 'Create');
?>
</body>
</html>
