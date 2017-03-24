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
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	selectFromList('User Name', 'user', $users, $row['user']);
	inputRow('email', 'email', $row['email'], 'email', 'george@spam.com');
	echo "<input type='hidden' name='oldqSMS' value='" . $row['qSMS'] . "'>\n";
	echo "<input type='hidden' name='oldqHTML' value='" . $row['qHTML'] . "'>\n";
	inputRow('Format as text', 'qFormat', 'qText', 'radio', NULL, false, NULL, NULL, NULL, 
		!$row['qSMS'] & !$row['qHTML']);
	inputRow('Format as SMS', 'qFormat', 'qSMS', 'radio', NULL, false, NULL, NULL, NULL, 
		$row['qSMS']);
	inputRow('Format as HTML', 'qFormat', 'qHTML', 'radio', NULL, false, NULL, NULL, NULL, 
		$row['qHTML']);
	foreach ($reports as $key => $value) {
		inputRow($value, 'report[]', $key, 'checkbox', NULL, false, NULL, NULL, NULL, 
			 !empty($emailReports[$row['id']][$key]));
	}
	echo "</table>\n";
	submitDelete($submit, !empty($row['email']));
	echo "</form>\n";
	echo "</center>\n";
}

$users = [];
$results = $parDB->loadTable('user', 'id', 'name', 'name');

$reports = [];
$results = $parDB->loadTable('reports', 'id', 'label', 'label');

$emailReports = [];
$results = $parDB->query('SELECT email,report FROM emailReports;');
while ($row = $results->fetchArray()) {
	$emailReports[$row['email']][$row['report']] = 1;
}

$results = $parDB->query("SELECT * FROM $table ORDER BY email;");
while ($row = $results->fetchArray()) {
	myForm($row, $users, $reports, $emailReports, 'Update');
}

$blankRow = array_fill_keys($fields, '');
$blankRow['id'] = -1;
myForm($blankRow, $users, $reports, $emailReports, 'Create');
?>
</body>
</html>
