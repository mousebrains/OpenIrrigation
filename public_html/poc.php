<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Point-of-connect editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'poc';
$fields = ['site', 'name', 'targetFlow', 'maxFlow', 'delayOn', 'delayOff'];

if (!empty($_POST)) {postUp($_POST, $table, $fields, $parDB);}

function myForm(array $row, array $sites, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	selectFromList('Site', 'site', $sites, $row['site']);
	inputRow('Name', 'name', $row['name'], 'text', 'Sensor Name', true);
	inputRow('Target Flow (GPM)', 'targetFlow', $row['targetFlow'], 
			'number', '1.5', false, 0.1, 0, 1000);
	inputRow('Maximum Flow (GPM)', 'maxFlow', $row['maxFlow'], 
			'number', '100', false, 0.1, 0, 1000);
	inputRow('Delay after On (s)', 'delayOn', $row['delayOn'], 
			'number', '1', false, 1, 0, 900);
	inputRow('Delay after Off (s)', 'delayOff', $row['delayOff'], 
			'number', '1', false, 1, 0, 900);
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

myForm(mkBlankRow($fields, ['id'=>'', 'site'=>key($sites)]), $sites, 'Create');
?>
</body>
</html>
