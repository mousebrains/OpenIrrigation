<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Controller Editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'controller';
$fields = ['site', 'name', 'latitude', 'longitude', 'driver', 
	'maxStations', 'maxCurrent', 'delay', 'make', 'model',
	'installed', 'notes'];

if (!empty($_POST)) {postUp($_POST, $table, $fields, $parDB);}

function myForm(array $row, array $sites, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	selectFromList('Site Name', 'site', $sites, $row['site']);
	inputRow('Controller Name', 'name', $row['name'], 'text', 'Controller Name');
	inputRow('Latitude (deg)', 'latitude', $row['latitude'], 'latlon', '23.45');
	inputRow('Longitude (deg)', 'longitude', $row['longitude'], 'latlon', '-85.4');
	inputRow('Driver', 'driver', $row['driver'], 'text', 'TDI');
	inputRow('Maximum simultaneous stations', 'maxStations', $row['maxStations'], 
		'number', '1', false, NULL, 1, 100);
	inputRow('Maximum allowed current (mAmps)', 'maxCurrent', $row['maxCurrent'], 
		'number', '9999', false, NULL, 20, 10000);
	inputRow('Delay between station operations (s)', 'delay', $row['delay'], 
		'number', '1', false, NULL, 0, 900);
	inputRow('Make', 'make', $row['make'], 'text', 'Tucor');
	inputRow('Model', 'model', $row['model'], 'text', 'TDI');
	inputRow('Installed on', 'installed', $row['installed'], 'date', '2007-10-23');
	inputRow('Notes', 'notes', $row['notes'], 'text', 'Something interesting');
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$sites = $parDB->loadTable('site', 'id', 'name', 'name');

$results = $parDB->query("SELECT * FROM $table ORDER BY name;");
while ($row = $results->fetchArray()) {
	myForm($row, $sites, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'','site'=>key($sites)]), $sites, 'Create');
?>
</body>
</html>
