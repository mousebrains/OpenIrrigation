<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
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

$table = 'email';
$fields = ['user', 'email', 'qSMS', 'qHTML'];

if (!empty($_POST)) {
	if (!empty($_POST['delete'])) { // Delete the entry
		$parDB->deleteFromTable($table, 'id', $_POST['id']);
	} else {
		$_POST['qSMS'] = $_POST['qFormat'] == 'qSMS';
		$_POST['qHTML'] = $_POST['qFormat'] == 'qHTML';
		if ($_POST['id'] < 0) { // A new entry
			$parDB->insertIntoTable($table, $fields, $_POST);
			$_POST['id'] = $parDB->getID($table, 'id', 'email', $_POST['email']);
		} else { // An existing entry
			$parDB->maybeUpdate($table, $fields, $_POST);
		} // Wrote an existing entry
		$parDB->deleteFromTable('emailReports', 'email', $_POST['id']);
		$stmt = $parDB->prepare('INSERT INTO emailReports VALUES(:email,:report);');
		foreach ($_POST['report'] as $key) { // Create new entries
			$stmt->bindValue(':email', $_POST['id']);
			$stmt->bindValue(':report', $key);
			$stmt->execute();
			$stmt->reset();
		}
		$stmt->close();

	}
}

function myForm(array $row, array $users, array $reports, array $emailReports, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	selectFromList('User Name', 'user', $users, $row['user']);
	inputRow('email', 'email', $row['email'], 'email', ['placeholder'=>'george@spam.com']);
	inputHidden($row['qSMS'], 'oldqSMS');
	inputHidden($row['qHTML'], 'oldqHTML');
	$checked = ['checked'=>NULL];
	inputRow('Format as text', 'qFormat', 'qText', 'radio', 
		(!$row['qSMS'] & !$row['qHTML']) ? $checked : []);
	inputRow('Format as SMS', 'qFormat', 'qSMS', 'radio', $row['qSMS'] ? $checked : []);
	inputRow('Format as HTML', 'qFormat', 'qHTML', 'radio', $row['qHTML'] ? $checked : []);
	foreach ($reports as $key => $value) {
		inputRow($value, 'report[]', $key, 'checkbox', 
			 !empty($emailReports[$row['id']][$key]) ? $checked : []);
	}
	echo "</table>\n";
	submitDelete($submit, !empty($row['email']));
	echo "</form>\n";
	echo "</center>\n";
}

$users = $parDB->loadTable('user', 'id', 'name', 'name');
$reports = $parDB->loadTable('reports', 'id', 'label', 'label');
$emailReports = $parDB->loadTableKeyValue('emailReports', 'email', 'report');

$results = $parDB->query("SELECT * FROM $table ORDER BY email COLLATE NOCASE;");
while ($row = $results->fetchArray()) {
	myForm($row, $users, $reports, $emailReports, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>-1,'user'=>key($users)]), 
	$users, $reports, $emailReports, 'Create');
?>
</body>
</html>
