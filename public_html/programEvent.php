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

$table = 'programEvent';
$fields = ['pgm', 'event', 'attractorFrac', 'priority'];

if (!empty($_POST)) {$parDB->postupArray($table, $fields, $_POST);}

function myRow(array $row, array $programs, array $events) {
	echo "<tr>\n<td>\n";
	inputHidden($row['id'], 'id[]');
	inputHidden($row['id'], 'delete[]', 'checkbox');
	echo "</td>\n";
	selectCellList('pgm[]', $programs, $row['pgm']);
	selectCellList('event[]', $events, $row['event']);
	echo "<td>\n";
	inputBlock('priority[]', $row['priority'], 'number', ['placeholder'=>1, 'min'=>0]);
	echo "</td>\n<td>\n";
	inputBlock('attractorFrac[]', $row['attractorFrac'], 'number', 
		['placeholder'=>1, 'step'=>0.05, 'min'=>0, 'max'=>1]);
	echo "</td>\n";
	echo "</tr>\n";
}

$programs = $parDB->loadTable('program', 'id', 'name', 'name');
$events = $parDB->loadTable('event', 'id', 'name', 'name');

echo "<center>\n";
echo "<form method='post'>\n";
echo "<table>\n";
echo "<tr>\n";
echo "<th>Delete</th>\n";
if (count($programs) > 1) {echo "<th>Program</th>\n";}
if (count($events) > 1) {echo "<th>Event</th>\n";}
echo "<th>Priority</th>\n";
echo "<th>Attractor Frac</th>\n";
echo "</tr>\n";
// Inner join needed for order by, ordering on pgm does not seem to work
$sql = "SELECT $table.id as id,"  . implode(',', $fields) . " FROM $table INNER JOIN program " .
	"ON pgm==program.id ORDER BY program.name,priority COLLATE NOCASE;";
$results = $parDB->query($sql);
while ($row = $results->fetchArray()) {
	myRow($row, $programs, $events);
}

myRow(mkBlankRow($fields, ['id'=>'','pgm'=>key($programs),'event'=>key($events)]), 
	$programs, $events);
echo "</table>\n";
echo "<input type='submit' value='Update'>\n";
echo "</form>\n";
echo "</center>\n";
echo "</table>\n";
echo "</form>\n";
echo "</center>\n";
?>
</body>
</html>
