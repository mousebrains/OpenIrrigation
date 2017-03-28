<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Wild Iris Irrigation</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/CmdDB.php';

if (!empty($_POST)) {
	$stime = time();
	$etime = $stime + $_POST['time'] * 60;
	$stmt = $cmdDB->prepare('INSERT INTO commands (valve,cmd,timestamp,src) '
			. ' VALUES(:stn,:cmd,:ts,:src);');
	$stmt->bindValue(':stn', $_POST['id']);
	$stmt->bindValue(':cmd', 0);
	$stmt->bindValue(':ts', $stime);
	$stmt->bindValue(':src', -1);
	$stmt->execute();
	$stmt->reset();
	$stmt->bindValue(':stn', $_POST['id']);
	$stmt->bindValue(':cmd', 1);
	$stmt->bindValue(':ts', $etime);
	$stmt->bindValue(':src', -1);
	$stmt->execute();
	$stmt->close();
}

function mkRow(array $row) {
	echo "<tr>\n<th>" . $row['name'] . "</th>\n";
	echo "<td>\n";
	echo "<form method='post'>\n";
        echo "<input type='hidden' name='id' value='" . $row['addr'] . "'>\n";
	echo "<input type='number' name='time' min='0' max='300'>\n";
	echo "<input type='submit' value='Run'>\n";
	echo "</form>\n";
	echo "</td>\n";
	echo "</tr>\n";
}

$hdr = "<tr><th>Station</th><th>Minutes</th></tr>";
echo "<center>\n<table>\n";
echo "<thead>$hdr</thead>\n";

$results = $parDB->query("SELECT sensor.addr,pocMV.name FROM pocMV "
		. "INNER JOIN sensor ON pocMV.sensor==sensor.id ORDER BY pocMV.name;");
while ($row = $results->fetchArray()) { mkRow($row); }


$results = $parDB->query("SELECT sensor.addr,station.name FROM station "
		. "INNER JOIN sensor ON station.sensor==sensor.id ORDER BY station.name");
while ($row = $results->fetchArray()) { mkRow($row); }

echo "<tfoot>$hdr</tfoot>\n";
echo "</table>\n</center>\n";
?>
</body>
</html> 
