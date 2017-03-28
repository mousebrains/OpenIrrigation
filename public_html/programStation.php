<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Report Name Editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

function myUpdate($table, $id, $name, $prev, $field) {
	global $parDB;
	if ($name != $prev) {
		$parDB->update($table, $field, $name, $id);
	}
}

$table = 'programStation';
$fields = ['pgm', 'stn', 'mode', 'runTime', 'priority'];
$adjust = ['runTime'=>60]; // Convert runTime min->sec

if (!empty($_POST)) {
	$parDB->postUpArray($table, $fields, $_POST, $adjust);
}

function myRow(array $row, array $programs, array $stations, array $modes) {
	global $parDB;
	global $adjust;
	echo "<tr>\n<td>\n";
	inputHidden($row['id'], 'id[]');
	inputHidden($row['pgm'], 'pgm[]');
	inputHidden($row['pgm'], 'oldpgm[]');
	inputHidden($row['id'], 'delete[]', 'checkbox');
	echo "</td>\n";
	selectCellList('stn[]', $stations, $row['stn']);
	selectCellList('mode[]', $modes, $row['mode']);
	echo "<td>\n";
	inputBlock('runTime[]', $parDB->unadjust('runTime', $row['runTime'], $adjust), 'number', 
		['step'=>0.1, 'min'=>1, 'max'=>600]);
	echo "</td>\n<td>\n";
	inputBlock('priority[]', $row['priority'], 'number', ['min'=>0]);
	echo "</td>\n";
	echo "</tr>\n";
}

$programs = $parDB->loadTable('program', 'id', 'name', 'name');
$stations = $parDB->loadTable('station', 'id', 'name', 'name');
$modes = $parDB->loadTable('programMode', 'id', 'label', 'label');

$stmt = $parDB->prepare("SELECT * FROM $table WHERE pgm==:pgm ORDER BY priority;");

foreach ($programs as $key => $name) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<h3>Program: $name</h3>\n";
	echo "<form method='post'>\n";
	echo "<table>\n";
	echo "<tr><th>Delete</th><th>Station</th><th>Mode</th>";
	echo "<th>RunTime<br>(min)</th><th>Priority</th></tr>\n";
	$stmt->bindValue(':pgm', $key);
	$results = $stmt->execute();
	while ($row = $results->fetchArray()) {
		myRow($row, $programs, $stations, $modes);
	}
	$stmt->reset();
	myRow(mkBlankRow($fields, ['id'=>'', 'pgm'=>$key, 'stn'=>key($stations),
                	'mode'=>key($modes), 'runTime'=>60]), 
		$programs, $stations, $modes);

	echo "</table>\n";
	echo "<input type='submit' value='Update'>\n";
	echo "</form>\n";
	echo "</center>\n";
}

$stmt->close();
?>
</body>
</html>
