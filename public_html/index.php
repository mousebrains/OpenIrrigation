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
        if (array_key_exists('Run', $_POST)) { // Update pgmStn
          $stmt = $parDB->prepare('INSERT OR REPLACE INTO pgmStn'
		. ' (program,mode,station,runTime,qSingle)'
		. ' SELECT (SELECT id FROM program WHERE name="Manual")'
		. ',(SELECT id FROM webList WHERE grp="pgm" AND key="on")'
		. ',:stn,:rt,1;');
          $stmt->bindValue(':stn', $_POST['id'], SQLITE3_INTEGER);
          $stmt->bindValue(':rt', $_POST['time']*60, SQLITE3_INTEGER);
          $stmt->execute();
          $stmt->close();
          $parDB->exec('INSERT OR REPLACE INTO scheduler VALUES(strftime("%s", "NOW"));');
        } else { // Stop an existing run
          $stmt = $parDB->prepare('DELETE FROM pgmStn'
		. ' WHERE program==(SELECT id FROM program WHERE name=="Manual")'
		. ' AND station==:stn;');
          $stmt->bindValue(':stn', $_POST['id'], SQLITE3_INTEGER);
          $stmt->execute();
          $stmt->close();
          $pgmId = $parDB->querySingle('SELECT id FROM program WHERE name=="Manual";');
          $stmt = $parDB->prepare('SELECT sensor.addr FROM sensor'
		. ' INNER JOIN station ON station.sensor==sensor.id AND station.id==:stn;');
          $stmt->bindValue(':stn', $_POST['id'], SQLITE3_INTEGER);
          $addr = $stmt->execute()->fetchArray()['addr'];
          $stmt->close();
          $stmt = $cmdDB->prepare('UPDATE commands SET timestamp=:now WHERE addr==:addr AND program==:pgm;');
          $stmt->bindValue(':now', time());
          $stmt->bindValue(':addr', $addr, SQLITE3_INTEGER);
          $stmt->bindValue(':pgm', $pgmId, SQLITE3_INTEGER);
          $stmt->execute();
          $stmt->close();
        }
}

function mkRow(array $row) {
	$id = $row['id'];
	echo "<tr>\n<th id='n$id'>" . $row['name'] . "</th>\n";
	echo "<td>\n";
        echo "<span id='a$id' style='display:inline;'>\n";
	echo "<form method='post'>\n";
        echo "<input type='hidden' name='id' value='$id'>\n";
	echo "<input type='number' name='time' min='0' max='300' step='0.1'>\n";
	echo "<input type='submit' name='Run' value='Run'>\n";
	echo "</form>\n";
        echo "</span>\n";
        echo "<span id='b$id' style='display:none;'>\n";
        echo "<span id='bc$id'></span>\n";
	echo "<form method='post' style='display:inline;'>\n";
        echo "<input type='hidden' name='id' value='$id'>\n";
	echo "<input type='submit' name='Stop' value='Stop'>\n";
	echo "</form>\n";
        echo "</span>\n";
	echo "</td>\n";
	echo "</tr>\n";
}

$hdr = "<tr><th>Station</th><th>Minutes</th></tr>";
echo "<center>\n<table>\n";
echo "<thead>$hdr</thead>\n";


$results = $parDB->query("SELECT id,name FROM station ORDER BY station.name");
while ($row = $results->fetchArray()) { mkRow($row); }

echo "<tfoot>$hdr</tfoot>\n";
echo "</table>\n</center>\n";
?>
<script src='js/index.js'></script>
</body>
</html> 
