<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Monitor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';

$thead = "<tr><th>Station</th><th>Prev<br>24 hrs</th><th>Next<br>24 hrs</th></tr>";
echo "<center>\n";
echo "<table>\n";
echo "<thead>$thead</thead>\n";
echo "<tbody>\n";

try {
  $results = $db->execute("SELECT id,name FROM station ORDER BY station.name;");
  while ($row = $results->fetchArray()) {
    $id = $row[0];
    $name = $row[1];
    echo "<tr id='r$id' style='display:none;'>"
	. "<th id='a$id'>$name</th>"
	. "<td id='p$id'></td>"
	. "<td id='n$id'></td>"
	. "</tr>\n";
  }
} catch (Exception $e) {
  echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
}

echo "</tbody>\n";
echo "<tfoot>$thead</tfoot>\n";
echo "</table>\n";
echo "</center>\n";
?>
<script src="js/smonitor.js"></script>
</body>
</html> 
