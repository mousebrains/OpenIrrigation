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

function mkRT($dt) {
  return sprintf('%d:%02d', floor($dt / 3600), intval(($dt % 3600) / 60));
}

try {
  $nBack = 8;
  $nFwd = 8;

  $now = new DateTimeImmutable();
  $format = 'Y-m-d H:i:s';

  $names = $db->loadKeyValue("SELECT id,name FROM station;");
  $stations = [];
  $past = [];
  $future = [];

  // currently active entries
  $results = $db->execute("SELECT station,sum($1-tOn),sum(tOff-$1) FROM active GROUP BY station;",
			  [$now->format($format)]);
  while ($row = $results->fetchRow()) {
    $a = $row[0];
    $past[$a][0] = $row[1];
    $future[$a][0] = $row[2];
    array_push($stations, $a);
  }

  // Past enteries
  $results = $db->execute("SELECT station,sum(tOff-tOn),date_trunc('day',tOn)"
		. " FROM historical"
		. " WHERE tOn>=$1"
		. " GROUP BY station,date_trunc('day',tOn);",
		[$now->sub(new DateInterval("P" . $nBack . "D"))->format($format)]);

  while ($row = $results->fetchArray()) {
    $a = $row[0];
    if (!array_key_exists($a, $past)) {$past[$a] = [];}
    $n = intval(floor(($now - $row[2]) / 86400));
    if (!array_key_exists($n, $past[$a])) {$past[$a][$n] = 0;}
    $past[$a][$n] += $row[1];
    array_push($stations, $a);
  }

  // Future enteries
  $results = $db->execute("SELECT station,sum(tOff-tOn),date_trunc('day',tOn)"
		  . " FROM pending"
		  . " WHERE tOn<=$1"
		  . " GROUP BY station,date_trunc('day',tOn);",
		  [$now->add(new DateInterval("P" . $nFwd . "D"))->format($format)]);
  while ($row = $results->fetchArray()) {
    $a = $row[0];
    if (!array_key_exists($a, $future)) {$future[$a] = [];}
    $n = intval(floor(($row[2]-$now) / 86400));
    if (!array_key_exists($n, $future[$a])) {$future[$a][$n] = 0;}
    $future[$a][$n] += $row[1];
    array_push($stations, $a);
  }

} catch (Exception $e) {
  echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
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

$stations = array_unique($stations);
$entries = [];
foreach ($stations as $stn) {
  if (array_key_exists($stn, $names)) {$entries[$names[$stn]] = $stn;}
}
ksort($entries);

foreach ($entries as $name => $stn) {
  echo "<tr>\n";
  if (array_key_exists($stn, $past)) {
    for ($j = $nBack-1; $j >= 0; $j--) {
      if (array_key_exists($j, $past[$stn])) {
        echo "<td>" . mkRT($past[$stn][$j]) . "</td>\n";
      } else {
        echo "<td></td>\n";
      }
    }
  } else {
    for ($j = $nBack-1; $j >= 0; $j--) {
      echo "<td></td>\n";
    }
  }
  echo "<th>$name</th>\n";
  if (array_key_exists($stn, $future)) {
    for ($j = 0; $j < $nFwd; $j++) {
      if (array_key_exists($j, $future[$stn])) {
        echo "<td>" . mkRT($future[$stn][$j]) . "</td>\n";
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
