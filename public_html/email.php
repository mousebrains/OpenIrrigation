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

if (!empty($_POST)) {
	if (!empty($_POST['delete'])) { // Delete the entry
		$stmt = $parDB->prepare('DELETE FROM email WHERE id=:id;');
		$stmt->bindValue(':id', $_POST['id']);
		$stmt->execute();
		$stmt->close();
	} else {
		if ($_POST['id'] < 0) { // A new entry
			$stmt = $parDB->prepare('INSERT OR REPLACE INTO email ' .
				'(email,qSMS,qHTML) VALUES(:email,:qSMS,:qHTML);');
			$stmt->bindValue(':email', $_POST['email']);
			$stmt->bindValue(':qSMS', $_POST['qFormat'] == 'qSMS');
			$stmt->bindValue(':qHTML', $_POST['qFormat'] == 'qHTML');
			$stmt->execute();
			$stmt->close();
			$stmt = $parDB->prepare('SELECT id FROM email WHERE email==:email;');
			$stmt->bindValue(':email', $_POST['email']);
			$result = $stmt->execute();
			while ($row = $result->fetchArray()) {
				$_POST['id'] = $row['id'];
				break;
			}
		} else { // An existing entry
			$stmt = $parDB->prepare('UPDATE email SET ' .
				'email=:email,' .
				'qSMS=:qSMS,' .
				'qHTML=:qHTML' .
				' WHERE id==:id;');
			$stmt->bindValue(':id', $_POST['id']);
			$stmt->bindValue(':email', $_POST['email']);
			$stmt->bindValue(':qSMS', $_POST['qFormat'] == 'qSMS');
			$stmt->bindValue(':qHTML', $_POST['qFormat'] == 'qHTML');
			$stmt->execute();
			$stmt->close();
		} // Wrote an existing entry
		{ // Delete existing entries
			$stmt = $parDB->prepare('DELETE FROM emailReports WHERE email==:email;');
			$stmt->bindValue(':email', $_POST['id']);
			$stmt->execute();
			$stmt->close();
		}
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

function myReport(int $id, int $key, string $value, array $emailReports) {
	echo "<tr><th>" . $value . "</th><td>\n";
	echo "<input type='checkbox', name='report[]', value='" . $key . "'";
	if (!empty($emailReports[$id][$key])) {
		echo " checked";
	}
	echo ">\n</td></tr>\n";
}

function myRadio($label, $name, $value, $qChecked) {
	echo "<tr><th>" . $label . "</th><td>\n";
	echo "<input type='radio' name='" . $name . "' value='" . $value . "'";
	if ($qChecked) {echo " checked";}
	echo "></td></tr>\n";
}

function myForm(array $row, array $reports, array $emailReports, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	echo "<tr><th>email</th><td>\n";
	echo "<input type='email' name='email' value='" . $row['email'] . 
		"' placeholder='email'>\n";
	echo "</td></tr>\n";
	myRadio('Format as text', 'qFormat', 'qText', !$row['qSMS'] & !$row['qHTML']);
	myRadio('Format as SMS', 'qFormat', 'qSMS', $row['qSMS']);
	myRadio('Format as HTML', 'qFormat', 'qHTML', $row['qHTML']);
	foreach ($reports as $key => $value) {
		myReport($row['id'], $key, $value, $emailReports);
	}
	echo "</table>\n";
	echo "<input type='submit' value='" . $submit . "'>\n";
	if (!empty($row['email'])) {
		echo "<input type='submit' value='Delete' name='delete'>\n";
	}
	echo "</form>\n";
	echo "</center>\n";
}

$reports = [];
$results = $parDB->query('SELECT id,label FROM reports ORDER BY label;');
while ($row = $results->fetchArray()) {
	$reports[$row['id']] = $row['label'];
}

$emailReports = [];
$results = $parDB->query('SELECT * FROM emailReports;');
while ($row = $results->fetchArray()) {
	$emailReports[$row['email']][$row['report']] = 1;
}

$results = $parDB->query('SELECT * FROM email ORDER BY email;');
while ($row = $results->fetchArray()) {
	myForm($row, $reports, $emailReports, 'Update');
}
myForm(['id'=>-1,'email'=>'','qSMS'=>0,'qHTML'=>0], $reports, $emailReports, 'Create');
?>
</body>
</html>
