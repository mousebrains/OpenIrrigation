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

function fmtTime($t) {
  if ($t < 0) {return '';}
  $t = round($t);
  return sprintf('%d:%02d:%02d', floor($t / 3600), floor(($t % 3600) / 60), $t % 60);
}

$now = time();
$past = [];
$pending = [];

$names = $parDB->loadTable("station INNER JOIN sensor ON station.sensor==sensor.id", 
	"sensor.addr", "station.name");

$results = $cmdDB->query("SELECT addr,sum($now-tOn),sum(tOff-$now) FROM onOffActive GROUP BY addr;");
while ($row = $results->fetchArray()) {
  $addr = $names[$row[0]];
  if (!array_key_exists($addr, $past)) {$past[$addr] = 0;}
  $past[$addr] += $row[1];
  if (!array_key_exists($addr, $pending)) {$pending[$addr] = 0;}
  $pending[$addr] += $row[2];
}

$now0 = $now - 86400;
$results = $cmdDB->query("SELECT addr,sum(tOff-max($now0,tOn)) FROM onOffHistorical"
	. " WHERE tOff>=$now0 GROUP BY addr;");
while ($row = $results->fetchArray()) {
  $addr = $names[$row[0]];
  if (!array_key_exists($addr, $past)) {$past[$addr] = 0;}
  $past[$addr] += $row[1];
}

$now1 = $now + 86400;
$results = $cmdDB->query("SELECT addr,sum(min(tOff,$now1)-tOn) FROM onOffPending"
	. " WHERE tOn<=$now1 GROUP BY addr;");
while ($row = $results->fetchArray()) {
  $addr = $names[$row[0]];
  $addr = $names[$row[0]];
  if (!array_key_exists($addr, $pending)) {$pending[$addr] = 0;}
  $pending[$addr] += $row[2];
}

$keys = array_merge(array_keys($past), array_keys($pending));
sort($keys);

$thead = "<tr><th>Station</th><th>Prev<br>24 hrs</th><th>Next<br>24 hrs</th></tr>";
echo "<center>\n";
echo "<table>\n";
echo "<thead>$thead</thead>\n";
echo "<tbody>\n";
foreach ($keys as $key) {
  echo "<tr><th>$key</th><td>";
  if (array_key_exists($key, $past)) {echo fmtTime($past[$key]);}
  echo "</td><td>";
  if (array_key_exists($key, $pending)) {echo fmtTime($pending[$key]);}
  echo "</td></tr>\n";
}
echo "</tbody>\n";
echo "<tfoot>$thead</tfoot>\n";
echo "</table>\n";
echo "</center>\n";
?>
</body>
</html> 
