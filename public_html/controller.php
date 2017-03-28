<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<meta http-equiv='Content-Language' content='en'>
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
$adjust = ['installed'=>'date'];

if (!empty($_POST)) {$parDB->postUp($table, $fields, $_POST, $adjust);}

function myForm(array $row, array $sites, string $submit) {
	global $parDB;
	global $adjust;
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	selectFromList('Site Name', 'site', $sites, $row['site']);
	inputRow('Controller Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Controller Name']);
	inputRow('Latitude (deg)', 'latitude', $row['latitude'], 'latlon', 
		['placeholder'=>-23.45]);
	inputRow('Longitude (deg)', 'longitude', $row['longitude'], 'latlon',
		['placeholder'=>-123.45]);
	inputRow('Driver', 'driver', $row['driver'], 'text', ['placeholder'=>'TDI']);
	inputRow('Maximum simultaneous stations', 'maxStations', $row['maxStations'], 'number', 
		['placeholder'=>1, 'min'=>1, 'max'=>100]);
	inputRow('Maximum allowed current (mAmps)', 'maxCurrent', $row['maxCurrent'], 'number', 
		['placeholder'=>9999, 'min'=>20, 'max'=>10000]);
	inputRow('Delay between station operations (s)', 'delay', $row['delay'], 'number', 
		['placeholder'=>1, 'min'=>0, 'max'=>900]);
	inputRow('Make', 'make', $row['make'], 'text', ['placeholder'=>'Tucor']);
	inputRow('Model', 'model', $row['model'], 'text', ['placeholder'=>'TDI']);
	inputRow('Installed on', 'installed', 
		$parDB->unadjust('installed', $row['installed'], $adjust), 
		'date', ['placeholder'=>'2007-10-23']);
	inputRow('Notes', 'notes', $row['notes'], 'text', ['placeholder'=>'Something interesting']);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$sites = $parDB->loadTable('site', 'id', 'name', 'name');

$results = $parDB->query("SELECT * FROM $table ORDER BY name COLLATE NOCASE;");
while ($row = $results->fetchArray()) {
	myForm($row, $sites, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'','site'=>key($sites)]), $sites, 'Create');
?>
</body>
</html>
