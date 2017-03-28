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

if (!empty($_POST)) {$parDB->postUpArray($table, $fields, $_POST);}

function myRow(array $row, array $sites, array $modes) {
	echo "<tr>\n";
	echo "<td>\n";
	inputHidden($row['id'], 'id[]');
	inputHidden($row['id'], 'delete[]', 'checkbox');
	echo "</td>\n<td>\n";
	inputBlock('name[]', $row['name'], 'text', ['placeholder'=>'Pgm B', 'required'=>NULL]);
	echo "</td>\n";
	selectCellList('mode[]', $modes, $row['mode']);
	selectCellList('site[]', $sites, $row['site']);
	echo "<td>\n";
	inputBlock('maxStations[]', $row['maxStations'], 'number', 
		['placeholder'=>1, 'min'=>1, 'max'=>200]);
	echo "</td>\n<td>\n";
	inputBlock('maxFlow[]', $row['maxFlow'], 'number', 
		['placeholder'=>1.5, 'step'=>0.1, 'min'=>0.1, 'max'=>200]);
	echo "</td>\n";
	echo "</tr>\n";
}

$sites = $parDB->loadTable('site', 'id', 'name', 'name');
$modes = $parDB->loadTable('programMode', 'id', 'label', 'label');

echo "<center>\n";
echo "<form method='post'>\n";
echo "<table>\n";
echo "<tr><th>Delete</th><th>Name</th>";
if (count($sites) > 1) {echo "<th>Site</th>";}
echo "<th>Mode</th><th>Max #<br>Stations</th><th>Max Flow<br>(GPM)</th></tr>\n";

$results = $parDB->query("SELECT * FROM $table ORDER BY name COLLATE NOCASE;");
while ($row = $results->fetchArray()) {
	myRow($row, $sites, $modes);
}

myRow(mkBlankRow($fields, ['id'=>'','site'=>key($sites),'mode'=>key($modes), 'name'=>'New Pgm']), 
	$sites, $modes);

echo "</table>\n";
echo "<input type='submit' value='Update'>\n";
echo "</form>";
echo "</center>";
?>
</body>
</html>
