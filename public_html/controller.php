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

if (!empty($_POST)) {
	$table = 'controller';
	if (!empty($_POST['delete'])) { // Delete the entry
		$parDB->deleteFromTable($table, 'id', $_POST['id']);
	} else {
		$fields = ['site', 'name', 'latitude', 'longitude', 'driver', 
			'maxStations', 'maxCurrent', 'delay', 'make', 'model',
			'installed', 'notes'];
		if ($_POST['id'] < 0) { // A new entry
			$parDB->insertIntoTable($table, $fields, $_POST);
		} else { // An existing entry
			$parDB->maybeUpdate($table, $fields, $_POST);
		}
	}
}

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

$sites = [];
$siteNum = 0;
$results = $parDB->query('SELECT id,name FROM site ORDER BY name;');
while ($row = $results->fetchArray()) {
	$siteNum = $row['id']; // Used latter
	$sites[$siteNum] = $row['name'];
}

$blankRow = [];
$results = $parDB->query('SELECT * FROM controller ORDER BY name;');
while ($row = $results->fetchArray()) {
	foreach ($row as $key => $value) {$blankRow[$key] = '';}
	myForm($row, $sites, 'Update');
}

$blankRow['id'] = -1;
$blankRow['site'] = $siteNum;
myForm($blankRow, $sites, 'Create');
?>
</body>
</html>
