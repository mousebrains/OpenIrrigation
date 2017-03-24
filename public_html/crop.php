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
	inputRow('Rough planting date', 'plantDate', $row['plantDate'], 'text');
	inputRow('Inital Stage length (days)', 'Lini', $row['Lini'], 'number', '10', false,
		1, 0, 365);
	inputRow('Development Stage length (days)', 'Ldev', $row['Ldev'], 'number', '10', false,
		1, 0, 365);
	inputRow('Middle Season Stage length (days)', 'Lmid', $row['Lmid'], 'number', '10', false,
		1, 0, 365);
	inputRow('Late Season Stage length (days)', 'Llate', $row['Llate'], 'number', '10', false,
		1, 0, 365);
	inputRow('Kc Inital Stage', 'KcInit', $row['KcInit'], 'number', '10', false,
		0.1, 0, 365);
	inputRow('Kc Middle Stage', 'KcMid', $row['KcMid'], 'number', '10', false,
		0.1, 0, 365);
	inputRow('Kc at End Stage', 'KcEnd', $row['KcEnd'], 'number', '10', false,
		0.1, 0, 365);
	inputRow('Height (m)', 'height', $row['height'], 'number', '10', false,
		0.1, 0, 5);
	inputRow('Root Depth (m)', 'depth', $row['depth'], 'number', '10', false,
		0.1, 0, 5);
	inputRow('Maximum Allowed Depletion (%)', 'MAD', $row['MAD'], 'number', '10', false,
		5, 0, 100);
	inputRow('Comment', 'comment', $row['comment'], 'text', 'Something interesting');
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
