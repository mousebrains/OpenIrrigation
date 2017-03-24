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

function myUpdate($table, $id, $name, $prev, $field) {
	global $parDB;
	if ($name != $prev) {
		$parDB->update($table, $field, $name, $id);
	}
}

if (!empty($_POST)) {
	$table = 'reports';
	$ids = $_POST['id'];
	$names = $_POST['name'];
	$oldnames = $_POST['oldname'];
	$labels = $_POST['label'];
	$oldlabels = $_POST['oldlabel'];
	for ($i = 0; $i < count($ids); ++$i) {
		if ($ids[$i] > 0) {
			myUpdate($table, $ids[$i], $names[$i], $oldnames[$i], 'name');
			myUpdate($table, $ids[$i], $labels[$i], $oldlabels[$i], 'label');
		} elseif (!empty($names[$i]) and !empty($labels[$i])) {
			$parDB->insertIntoTable($table, ['name', 'label'], 
						['name'=>addslashes($names[$i]), 
						 'oldname'=>NULL,
						 'label'=>addslashes($labels[$i]),
						 'oldlabel'=>NULL]);
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

function myRow(array $row) {
	echo "<tr>\n";
        echo "<th><input type='hidden' name='id[]' value='" . $row['id'] . "'>";
	echo "<input type='checkbox' name='delete[]' value='" . $row['id'] . "'></th>\n";
	echo "<td>";
	echo "<input type='hidden' name='oldname[]' value='" . $row['name'] ."'>";
	echo "<input type='text' name='name[]' value='" . $row['name'] . 
		"' placeholder='short name'>";
	echo "</td>\n";	
	echo "<td>";
	echo "<input type='hidden' name='oldlabel[]' value='" . $row['label'] ."'>";
	echo "<input type='text' name='label[]' value='" . $row['label'] . 
		"' placeholder='descriptive name'>";
	echo "</td>\n";	
	echo "</tr>\n";
}

$reports = [];
$results = $parDB->query('SELECT * FROM reports ORDER BY name;');
while ($row = $results->fetchArray()) {
	array_push($reports, 
		['id' => $row['id'], 'name' => $row['name'], 'label' => $row['label']]);
}

echo "<center>\n";
echo "<form method='post'>\n";
echo "<table>\n";
echo "<tr><th>Delete</th><th>Short Name</th><th>Descriptive Name</th></tr>\n";
foreach ($reports as $row) {
	myRow($row);
}
myRow(['id'=>-1,'name'=>'','label'=>'']);
echo "</table>\n";
echo "<input type='submit' value='Update'>\n";
echo "</form>\n";
echo "</center>\n";
?>
</body>
</html>
