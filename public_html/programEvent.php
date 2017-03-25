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

$table = 'programEvent';
$fields = ['pgm', 'event', 'attractorFrac', 'priority'];

if (!empty($_POST)) {
	for ($i = 0; $i < count($_POST['id']); ++$i) {
		$id = $_POST['id'][$i];
		$a = ['id'=>$id];
		foreach ($fields as $field) {
			$a[$field] = $_POST[$field][$i];
			$a["old$field"] = $_POST["old$field"][$i];
		}
		if ($id > 0) {
			$parDB->maybeUpdate($table, $fields, $a);
		} else {
			$parDB->insertIntoTable($table, $fields, $a);
		}
	}
	if (!empty($_POST['delete'])) { // Delete the entry (Do 2nd so updates are overridden
		foreach ($_POST['delete'] as $id) {
			if ($id >= 0) {
				$parDB->deleteFromTable($table, 'id', $id);
			}
		}
	}
}

function mySelect(string $name, array $items, string $active) {
	echo "<td>\n";
	echo "<input type='hidden' name='old$name' value='$active'>\n";
	echo "<select name='$name'>\n";
	foreach ($items as $key => $value) {
		echo "<option value='$key'";
		if ($key == $active) {echo " selected";}
		echo ">$value</option>";
	}
	echo "<select>\n</td>\n";
}

function myRow(array $row, array $programs, array $events) {
	echo "<tr>\n";
        echo "<th><input type='hidden' name='id[]' value='" . $row['id'] . "'>";
	echo "<input type='checkbox' name='delete[]' value='" . $row['id'] . "'></th>\n";
	mySelect('pgm[]', $programs, $row['pgm']);
	mySelect('event[]', $events, $row['event']);
	echo "<td>\n";
	echo "<input type='hidden' name='oldpriority[]' value='" . $row['priority'] . "'>\n";
	echo "<input type='number' name='priority[]' value='" . $row['priority'] . 
		"' placeholder='1' min='0'>\n";
	echo "</td>\n";
	echo "<td>\n";
	echo "<input type='hidden' name='oldattractorFrac[]' value='" . $row['attractorFrac'] . "'>\n";
	echo "<input type='number' name='attractorFrac[]' value='" . $row['attractorFrac'] . 
		"' placeholder='0' step='0.01' min='0' max='1'>\n";
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
echo "<th>Program</th>\n";
echo "<th>Event</th>\n";
echo "<th>Priority</th>\n";
echo "<th>Attractor Frac</th>\n";
echo "</tr>\n";
// Inner join needed for order by, ordering on pgm does not seem to work
$sql = "SELECT $table.id as id,"  . implode(',', $fields) . " FROM $table INNER JOIN program " .
	"ON pgm==program.id ORDER BY program.name,priority;";
$results = $parDB->query($sql);
while ($row = $results->fetchArray()) {
	myRow($row, $programs, $events);
}
$blankRow = array_fill_keys($fields, '');
$blankRow['id'] = -1;
$blankRow['pgm'] = key($programs);
$blankRow['event'] = key($events);
myRow($blankRow, $programs, $events);
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
