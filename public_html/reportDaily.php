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

function mkRT($dt) {
  return sprintf('%d:%02d', floor($dt / 3600), intval(($dt % 3600) / 60));
}

$nBack = 8;
$nFwd = 8;

$name = [];
$addr = [];
$results = $parDB->query("SELECT sensor.addr,station.name FROM station"
	. " INNER JOIN sensor ON station.sensor==sensor.id"
	. " ORDER by station.name;");
while ($row = $results->fetchArray()) {
  array_push($addr, $row[0]); 
  array_push($name, $row[1]); 
}

$past = [];
$future = [];

$now = time();
$earliest = $now - ($nBack+1) * 86400;
$latest = $now + ($nFwd+1) * 86400;

// currently active entries
$results = $cmdDB->query("SELECT addr,sum($now-tOn),sum(tOff-$now)"
		. " FROM onOffActive GROUP BY addr;");
while ($row = $results->fetchArray()) {
  $a = $row[0];
  $past[$a][0] = $row[1];
  $future[$a][0] = $row[2];
}

// Past enteries
$results = $cmdDB->query("SELECT addr,sum(tOff-tOn),min(tOn) FROM onOffHistorical"
		. " WHERE tOn >= $earliest"
		. " GROUP BY addr,date(tOn,'unixepoch','localtime');");
while ($row = $results->fetchArray()) {
  $a = $row[0];
  if (!array_key_exists($a, $past)) {$past[$a] = [];}
  $n = intval(floor(($now - $row[2]) / 86400));
  if (!array_key_exists($n, $past[$a])) {$past[$a][$n] = 0;}
  $past[$a][$n] += $row[1];
}

// Future enteries
$results = $cmdDB->query("SELECT addr,sum(tOff-tOn),max(tOn) FROM onOffPending"
		. " WHERE tOn <= $latest"
		. " GROUP BY addr,date(tOn,'unixepoch','localtime');");
while ($row = $results->fetchArray()) {
  $a = $row[0];
  if (!array_key_exists($a, $future)) {$future[$a] = [];}
  $n = intval(floor(($row[2]-$now) / 86400));
  if (!array_key_exists($n, $future[$a])) {$future[$a][$n] = 0;}
  $future[$a][$n] += $row[1];
}

$thead0 = "<tr><th colspan='$nBack'>Recent</th><th rowspan='2'>Station</th><th colspan='$nFwd'>Future</th></tr>";
$tfoot1 = "<tr><th colspan='$nBack'>Recent</th><th colspan='$nFwd'>Future</th></tr>";
$tfoot0 = "<tr>";
$thead1 = "<tr>";
$now = time();
for ($cnt = $nBack-1; $cnt >= 0; $cnt--) {
  $date = $cnt == 0 ? "Today" : strftime("%m/%d", $now - $cnt * 86400);
  $thead1 .= "<th>$date</th>";
  $tfoot0 .= "<th>$date</th>";
}
$tfoot0 .= "<th rowspan='2'>Station</th>";
for ($cnt = 0; $cnt < $nFwd; $cnt++) {
  $date = $cnt == 0 ? "Today" : strftime("%m/%d", $now + $cnt * 86400);
  $thead1 .= "<th>$date</th>";
  $tfoot0 .= "<th>$date</th>";
}
$thead1 .= "</tr>";

echo "<center>\n";
echo "<table>\n";
echo "<thead>$thead0\n$thead1\n</thead>\n";
echo "<tbody>\n";

for ($i = 0; $i < count($addr); $i++) {
  $a = $addr[$i];
  if (!array_key_exists($a, $past) and !array_key_exists($a, $future)) { continue; }
  echo "<tr>\n";
  if (array_key_exists($a, $past)) {
    for ($j = $nBack-1; $j >= 0; $j--) {
      if (array_key_exists($j, $past[$a])) {
        echo "<td>" . mkRT($past[$a][$j]) . "</td>\n";
      } else {
        echo "<td></td>\n";
      }
    }
  } else {
    for ($j = $nBack-1; $j >= 0; $j--) {
      echo "<td></td>\n";
    }
  }
  echo "<th>" . $name[$i] . "</th>\n";
  if (array_key_exists($a, $future)) {
    for ($j = 0; $j < $nFwd; $j++) {
      if (array_key_exists($j, $future[$a])) {
        echo "<td>" . mkRT($future[$a][$j]) . "</td>\n";
      } else {
        echo "<td></td>\n";
      }
    }
  } else {
    for ($j = 0; $j < $nFwd; $j++) {
      echo "<td></td>\n";
    }
  }
  echo "</tr>\n";
}

echo "</tbody>\n";
echo "<tfoot>\n$tfoot0\n$tfoot1\n</tfoot>\n";
echo "</table>\n";
echo "</center>\n";
?>
</body>
</html> 
