<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
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

if (!empty($_POST)) {$parDB->postUp($table, $fields, $_POST);}

function myForm(array $row, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	inputRow('Site Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Site Name', 'required'=>NULL]);
	inputRow('Address', 'addr', $row['addr'], 'text', 
		['placeholder'=>'1600 Penn Ave, Washington, D.C.']);
	inputRow('Timezone', 'timezone', $row['timezone'], 'text', 
		['placeholder'=>'US/Eastern']);
	inputRow('Latitude (deg)', 'latitude', $row['latitude'], 'latlon', 
		['placeholder'=>-23.45]);
	inputRow('Longitude (deg)', 'longitude', $row['longitude'], 'latlon', 
		['placeholder'=>-123.45]);
	inputRow('Elevation (ft)', 'elevation', $row['elevation'], 'number', 
		['placeholder'=>14500, 'min'=>-1000,'max'=>20000]);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$results = $parDB->query("SELECT * FROM $table ORDER BY name COLLATE NOCASE;");
while ($row = $results->fetchArray()) {
	myForm($row, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'']), 'Create')
?>
</body>
</html>
