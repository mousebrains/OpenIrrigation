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

if (!empty($_POST)) {
	if (!empty($_POST['delete'])) { // Delete the entry
		$parDB->deleteFromTable($table, 'id', $_POST['id']);
	} else {
		if ($_POST['id'] == '') {
			$parDB->insertIntoTable($table, $fields, $_POST);	
		} else {
			$parDB->maybeUpdate($table, $fields, $_POST);	
		}
	}
}

function myForm(array $row, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	inputRow('Crop Name', 'name', $row['name'], 'text', 'Joe Smith', true);
	inputRow('Plant Available Water (mm/m)', 'paw', $row['paw'], 'number', '10', false,
		1, 0, 1000);
	inputRow('Infiltration Rate (mm/hour)', 'infiltration', $row['infiltration'], 
		'number', '10', false, 0.1, 0, 1000);
	inputRow('Infiltration Rate Slope (mm/hour/%)', 
		'infiltrationSlope', $row['infiltrationSlope'], 
		'number', '10', false, 0.01, 0, 1000);
	inputRow('Root Depth Normalization', 'rootNorm', $row['rootNorm'], 
		'number', '1.1', false, 0.1, 0, 5);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$results = $parDB->query("SELECT * FROM $table ORDER BY name;");
while ($row = $results->fetchArray()) {
	myForm($row, 'Update');
}

$blankRow = array_fill_keys($fields, '');
$blankRow['id'] = '';
myForm($blankRow, 'Create');
?>
</body>
</html>
