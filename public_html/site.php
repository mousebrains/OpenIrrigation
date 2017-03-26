<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Site editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'site';
$fields = ['name', 'addr', 'timezone', 'latitude', 'longitude', 'elevation'];

if (!empty($_POST)) {postUp($_POST, $table, $fields, $parDB);}

function myForm(array $row, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	inputRow('Site Name', 'name', $row['name'], 'text', 'Site Name', true);
	inputRow('Address', 'addr', $row['addr'], 'text', '1600 Penn Ave, Washington, D.C.');
	inputRow('Timezone', 'timezone', $row['timezone'], 'text', 'US/Eastern');
	inputRow('Latitude (deg)', 'latitude', $row['latitude'], 'latlon', '23.45');
	inputRow('Longitude (deg)', 'longitude', $row['longitude'], 'latlon', '123.45');
	inputRow('Elevation (ft)', 'elevation', $row['elevation'], 'number', '14500');
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$results = $parDB->query("SELECT * FROM $table ORDER BY name;");
while ($row = $results->fetchArray()) {
	myForm($row, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'']), 'Create')
?>
</body>
</html>
