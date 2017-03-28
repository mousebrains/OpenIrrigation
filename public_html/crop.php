<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Crop editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'crop';
$fields = ['name', 'plantDate', 'Lini', 'Ldev', 'Lmid', 'Llate',
	'KcInit', 'KcMid', 'KcEnd', 'height', 'depth', 'MAD', 'comment'];

if (!empty($_POST)) {$parDB->postUp($table, $fields, $_POST);}

function myForm(array $row, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	inputRow('Crop Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Joe Smith', 'required'=>NULL]);
	inputRow('Rough planting date', 'plantDate', $row['plantDate'], 'text',
		['placeholder'=>'March']);
	inputRow('Inital Stage length (days)', 'Lini', $row['Lini'], 'number', 
		['placeholder'=>10, 'min'=>0, 'max'=>365]);
	inputRow('Development Stage length (days)', 'Ldev', $row['Ldev'], 'number', 
		['placeholder'=>10, 'min'=>0, 'max'=>365]);
	inputRow('Middle Season Stage length (days)', 'Lmid', $row['Lmid'], 'number',
		['placeholder'=>10, 'min'=>0, 'max'=>365]);
	inputRow('Late Season Stage length (days)', 'Llate', $row['Llate'], 'number',
		['placeholder'=>10, 'min'=>0, 'max'=>365]);
	inputRow('Kc Inital Stage', 'KcInit', $row['KcInit'], 'number', 
		['placeholder'=>0.7, 'step'=>0.05, 'min'=>0, 'max'=>3]);
	inputRow('Kc Middle Stage', 'KcMid', $row['KcMid'], 'number',
		['placeholder'=>1.05, 'step'=>0.05, 'min'=>0, 'max'=>3]);
	inputRow('Kc at End Stage', 'KcEnd', $row['KcEnd'], 'number',
		['placeholder'=>0.95, 'step'=>0.05, 'min'=>0, 'max'=>3]);
	inputRow('Height (m)', 'height', $row['height'], 'number',
		['placeholder'=>0.95, 'step'=>0.025, 'min'=>0.025, 'max'=>4]);
	inputRow('Root Depth (m)', 'depth', $row['depth'], 'number',
		['placeholder'=>0.55, 'step'=>0.025, 'min'=>0.025, 'max'=>4]);
	inputRow('Maximum Allowed Depletion (%)', 'MAD', $row['MAD'], 'number',
		['placeholder'=>0.50, 'step'=>0.05, 'min'=>0.1, 'max'=>0.95]);
	inputRow('Comment', 'comment', $row['comment'], 'text', 
		['placeholder'=>'Something interesting']);
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
