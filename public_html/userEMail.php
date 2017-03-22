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

/*
if (!empty($_POST)) {
	if (!empty($_POST['delete'])) { // Delete the entry
		$stmt = $parDB->prepare('DELETE FROM user WHERE id=:id;');
		$stmt->bindValue(':id', $_POST['id']);
		$stmt->execute();
		$stmt->close();
	} else {
		if ($_POST['id'] == '') {
			$stmt = $parDB->prepare('INSERT INTO user (name,passwd) VALUES(:name,:passwd);');
		} else {
			$stmt = $parDB->prepare('INSERT OR REPLACE INTO user VALUES(:id,:name,:passwd);');
			$stmt->bindValue(':id', $_POST['id']);
		}
		$stmt->bindValue(':name', $_POST['name']);
		$hash = password_hash($_POST['passwd'], PASSWORD_DEFAULT);
		$stmt->bindValue(':passwd', $hash);
		$stmt->execute();
		$stmt->close();
	}
}
 */

function myRow(string $label, string $name, $value, string $type, $qRequired) {
	$msg = "<tr><th>" 
		. $label 
		. "</th><td>"
		. "<input type='" . $type . "' name='" 
		. $name
		. "' value='" 
		. $value
		. "' placeholder='"
		. $label
		. "'";
	if ($qRequired) {
		$msg .= " required";
	}
	$msg .= "></td></tr>\n";
	return $msg;
}

function myForm(array $row, string $submit) {
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<table>\n";
	echo myRow('User Name', 'name', $row['name'], 'text', true);
	echo myRow('Password', 'passwd', '', 'password', true);
	echo "</table>\n";
	echo "<input type='submit' value='" . $submit . "'>\n";
	if (!empty($row['name'])) {
		echo "<input type='submit' value='Delete' name='delete'>\n";
	}
	echo "</form>\n";
	echo "</center>\n";
}

$users = [];
$results = $parDB->query('SELECT id,name FROM user ORDER BY name;');
while ($row = $results->fetchArray()) {
	$users[$row['id']] = $row['name'];
}
echo '<pre>';
var_dump($users);
echo '</pre>';

$results = $parDB->query('SELECT * FROM userEMail ORDER BY email;');
while ($row = $results->fetchArray()) {
	$row['name'] = $users[$row['user']];
	echo '<pre>';
	var_dump($row);
	echo '</pre>';
}
?>
</body>
</html>
