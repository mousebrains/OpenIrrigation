<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Program editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'program';
$fields = ['site', 'name', 'mode', 'maxStations', 'maxFlow'];

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

function myForm(array $row, array $sites, array $modes, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	selectFromList('Site', 'site', $sites, $row['site']);
	selectFromList('Operating Mode', 'mode', $modes, $row['mode']);
	inputRow('Name', 'name', $row['name'], 'text', 'Program B', true);
	inputRow('Maximum Number Simultaneous Stations', 'maxStations', $row['maxStations'], 
		'number', '1', false, 1, 1, 200);
	inputRow('Maximum Flow (GPM)', 'maxFlow', $row['maxFlow'], 
		'number', '20.5', false, 0.1, 0.1, 200);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$sites = $parDB->loadTable('site', 'id', 'name', 'name');
$modes = $parDB->loadTable('programMode', 'id', 'label', 'label');

$results = $parDB->query('SELECT * FROM ' . $table . ' ORDER BY name;');
while ($row = $results->fetchArray()) {
	myForm($row, $sites, $modes, 'Update');
}

$blankRow = ['id'=>''];
foreach ($fields as $field) {$blankRow[$field] = '';}
myForm($blankRow, $sites, $modes, 'Create');
?>
</body>
</html>
