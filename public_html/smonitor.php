<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<meta http-equiv='refresh', content='15'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Monitor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/CmdDB.php';
require_once 'php/ParDB.php';

$thead = "<tr><th>Station</th><th>Prev<br>24 hrs</th><th>Next<br>24 hrs</th></tr>";
echo "<center>\n";
echo "<table>\n";
echo "<thead>$thead</thead>\n";
echo "<tbody>\n";

$results = $parDB->query("SELECT sensor.addr,station.name"
	. " FROM station INNER JOIN sensor ON station.sensor==sensor.id"
	. " ORDER BY station.name;");
while ($row = $results->fetchArray()) {
  $addr = $row[0];
  $name = $row[1];
  echo "<tr id='r$addr' style='display:none;'>"
	. "<th id='a$addr'>$name</th>"
	. "<td id='p$addr'></td>"
	. "<td id='n$addr'></td>"
	. "</tr>\n";
}

echo "</tbody>\n";
echo "<tfoot>$thead</tfoot>\n";
echo "</table>\n";
echo "</center>\n";
?>
<script src="js/smonitor.js"></script>
</body>
</html> 
