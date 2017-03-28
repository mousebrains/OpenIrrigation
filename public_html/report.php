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

$table = 'reports';
$fields = ['name', 'label'];

if (!empty($_POST)) {$parDB->postUpArray($table, $fields, $_POST);}

function myRow(array $row) {
	echo "<tr>\n<th>\n";
	inputHidden($row['id'], 'id[]');
	inputHidden($row['id'], 'delete[]', 'checkbox');
	echo "</th>\n<td>\n";
	inputBlock('name[]', $row['name'], 'text', ['placeholder'=>'Short Name']);
	echo "</td>\n<td>\n";	
	inputBlock('label[]', $row['label'], 'text', ['placeholder'=>'Descriptive name']);
	echo "</td>\n</tr>\n";	
}


echo "<center>\n";
echo "<form method='post'>\n";
echo "<table>\n";
echo "<tr><th>Delete</th><th>Short Name</th><th>Descriptive Name</th></tr>\n";

$results = $parDB->query("SELECT * FROM $table ORDER BY name COLLATE NOCASE;");
while ($row = $results->fetchArray()) { myRow($row); }

myRow(mkBlankRow($fields, ['id'=>'']));
echo "</table>\n";
echo "<input type='submit' value='Update'>\n";
echo "</form>\n";
echo "</center>\n";
?>
</body>
</html>
