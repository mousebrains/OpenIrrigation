<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Soil editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'soil';
$fields = ['name', 'paw', 'infiltration', 'infiltrationSlope', 'rootNorm'];

if (!empty($_POST)) {$parDB->postUp($table, $fields, $_POST);}

function myForm(array $row, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	inputRow('Crop Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Joe Smith', 'required'=>NULL]);
	inputRow('Plant Available Water (mm/m)', 'paw', $row['paw'], 'number', 
		['placeholder'=>10, 'min'=>0, 'max'=>1000]);
	inputRow('Infiltration Rate (mm/hour)', 'infiltration', $row['infiltration'], 'number', 
		['placeholder'=>10, 'step'=>0.1, 'min'=>0, 'max'=>1000]);
	inputRow('Infiltration Rate Slope (mm/hour/%)', 'infiltrationSlope', 
		$row['infiltrationSlope'], 'number', 
		['placeholder'=>10, 'step'=>0.01, 'min'=>0, 'max'=>1000]);
	inputRow('Root Depth Normalization', 'rootNorm', $row['rootNorm'], 'number', 
		['placeholder'=>1.1, 'step'=>0.1, 'min'=>0, 'max'=>5]);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$results = $parDB->query("SELECT * FROM $table ORDER BY name COLLATE NOCASE;");
while ($row = $results->fetchArray()) {
	myForm($row, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'']), 'Create');
?>
</body>
</html>
