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

if (!empty($_POST)) {
	$table = 'user';
	if (!empty($_POST['delete'])) { // Delete the entry
		$parDB->deleteFromTable($table, 'id', $_POST['id']);
	} else {
		$fields = ['name', 'passwd'];
		if (!empty($_POST['passwd'])) { // Hash it
			$_POST['passwd'] = password_hash($_POST['passwd'], PASSWORD_DEFAULT); 
		}
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
	inputRow('User Name', 'name', $row['name'], 'text', 'Joe Smith', true);
	inputRow('Password', 'passwd', '', 'password', '1234567890');
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$blankRow = [];
$results = $parDB->query('SELECT * FROM user ORDER BY name;');
while ($row = $results->fetchArray()) {
	foreach ($row as $key => $value) {$blankRow[$key] = '';}
	myForm($row, 'Update');
}

myForm($blankRow, 'Create');
?>
</body>
</html>
