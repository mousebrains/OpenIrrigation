<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Site editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';

if (!empty($_POST)) {
	if (!empty($_POST['delete'])) { // Delete the entry
		$stmt = $parDB->prepare('DELETE FROM site WHERE id=:id;');
		$stmt->bindValue(':id', $_POST['id']);
		$stmt->execute();
		$stmt->close();
	} else {
		if ($_POST['id'] == '') {
			$stmt = $parDB->prepare('INSERT INTO site (name,addr,timezone,latitude,longitude,elevation) VALUES(:name,:addr,:tz,:lat,:lon,:elev);');
		} else {
			$stmt = $parDB->prepare('INSERT OR REPLACE INTO site VALUES(:id,:name,:addr,:tz,:lat,:lon,:elev);');
			$stmt->bindValue(':id', $_POST['id']);
		}
		$stmt->bindValue(':name', $_POST['name']);
		$stmt->bindValue(':addr', $_POST['addr']);
		$stmt->bindValue(':tz', $_POST['timezone']);
		$stmt->bindValue(':lat', $_POST['latitude']);
		$stmt->bindValue(':lon', $_POST['longitude']);
		$stmt->bindValue(':elev', $_POST['elevation']);
		$stmt->execute();
		$stmt->close();
	}
}

function myRow(string $label, string $name, $value, $qRequired) {
	$msg = "<tr><th>" 
		. $label 
		. "</th><td>"
		. "<input type='text' name='" 
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
	echo myRow('Site Name', 'name', $row['name'], true);
	echo myRow('Address', 'addr', $row['addr'], false);
	echo myRow('Timezone', 'timezone', $row['timezone'], false);
	echo myRow('Latitude (deg)', 'latitude', $row['latitude'], false);
	echo myRow('Longitude (deg)', 'longitude', $row['longitude'], false);
	echo myRow('Elevation (ft)', 'elevation', $row['elevation'], false);
	echo "</table>\n";
	echo "<input type='submit' value='" . $submit . "'>\n";
	if (!empty($row['name'])) {
		echo "<input type='submit' value='Delete' name='delete'>\n";
	}
	echo "</form>\n";
	echo "</center>\n";
}

$results = $parDB->query('SELECT * FROM site ORDER BY name;');
while ($row = $results->fetchArray()) {
	myForm($row, 'Update');
}

myForm(array(
	'id' => '', 
	'name' => '', 
	'addr' => '', 
	'timezone' => '', 
	'latitude' => '', 
	'longitude' => '', 
	'elevation' => ''), 'Add');
?>
</body>
</html>
