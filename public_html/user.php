<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>User editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'user';
$fields = ['name', 'passwd'];
$adjust = ['passwd'=>'passwd'];

if (!empty($_POST)) {$parDB->postUp($table, $fields, $_POST, $adjust);}

function myForm(array $row, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	inputRow('User Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Joe Smith', 'required'=>NULL]);
	inputRow('Password', 'passwd', '', 'password', ['placeholder'=>'1234567890']);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$results = $parDB->query("SELECT * FROM $table ORDER BY name COLLATE NOCASE;");
while ($row = $results->fetchArray()) { myForm($row, 'Update'); }

myForm(mkBlankRow($fields, ['id'=>'']), 'Create');
?>
</body>
</html>
