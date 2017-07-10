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

function mkRt($dt) {
  $hours = floor($dt / 3600);
  $minutes = round(($dt % 3600) / 60);
  if ($minutes >= 60) {
    $hours += 1;
    $minutes -= 60;
  }
  return sprintf('%d:%02d', $hours, $minutes);
}

try {
  $nBack = 11;
  $nFwd = 11;

  $past = [];
  $future = [];

  $sql = "SELECT sensor"
		. ",date_part('epoch',tOff-tOn) as dt"
		. ",date_part('epoch',tOff-CURRENT_TIMESTAMP) as dtLeft"
		. ",date_part('epoch',CURRENT_TIMESTAMP-tOn) as dtDone"
		. ",CAST(tOn AS DATE)-CURRENT_DATE AS n"
		. " FROM everything"
  		. " WHERE tOn>=(CURRENT_DATE - INTERVAL '$nBack DAYS')"
		. " AND tOn<=(CURRENT_DATE + INTERVAL '$nFwd DAYS')"
		. ";";
  $results = $db->execute($sql);
  while ($row = $results->fetchRow()) {
    $id = $row[0];
    $dt = $row[1];
    $dtLeft = $row[2];
    $dtDone = $row[3];
    $n = $row[4];
    if ($n < 0) { // Past
      if (!array_key_exists($id, $past)) {$past[$id] = [];}
      if (!array_key_exists($n, $past[$id])) {$past[$id][$n] = 0;}
      $past[$id][$n] += $dt;
    } elseif ($n > 0) { // Future
      if (!array_key_exists($id, $future)) {$future[$id] = [];}
      if (!array_key_exists($n, $future[$id])) {$future[$id][$n] = 0;}
      $future[$id][$n] += $dt;
    } elseif ($dtLeft < 0) { // Today already done
      if (!array_key_exists($id, $past)) {$past[$id] = [];}
      if (!array_key_exists($n, $past[$id])) {$past[$id][$n] = 0;}
      $past[$id][$n] += $dt;
    } elseif ($dtDone < 0) { // Today yet to be done
      if (!array_key_exists($id, $future)) {$future[$id] = [];}
      if (!array_key_exists($n, $future[$id])) {$future[$id][$n] = 0;}
      $future[$id][$n] += $dt;
    } else { // Active
      if (!array_key_exists($id, $past)) {$past[$id] = [];}
      if (!array_key_exists($id, $future)) {$future[$id] = [];}
      if (!array_key_exists($n, $past[$id])) {$past[$id][$n] = 0;}
      if (!array_key_exists($n, $future[$id])) {$future[$id][$n] = 0;}
      $past[$id][$n] += $dtDone;
      $future[$id][$n] += $dtLeft;
    }
  }

  $stations = $db->loadKeyValue('SELECT sensor,name FROM station ORDER BY name;');

  $sens2pgm = [];
  $results = $db->execute("SELECT station.sensor,program.label FROM pgmStn"
		. " INNER JOIN program ON pgmStn.qSingle IS False AND pgmStn.program=program.id"
		. " INNER JOIN station ON pgmStn.station=station.id"
		. " ORDER BY program.label;");
  while ($row = $results->fetchRow()) {
    $key = $row[0];
    if (!array_key_exists($key, $sens2pgm)) {$sens2pgm[$key] = [];}
    array_push($sens2pgm[$key], $row[1]);
  }
} catch (Exception $e) {
  echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
}

$thead0 = "<tr><th colspan='$nBack'>Recent</th>"
	. "<th rowspan='2'>Station</th>"
	. "<th rowspan='2'>Program</th>"
	. "<th colspan='$nFwd'>Future</th></tr>";
$tfoot1 = "<tr><th colspan='$nBack'>Recent</th><th colspan='$nFwd'>Future</th></tr>";
$tfoot0 = "<tr>";
$thead1 = "<tr>";
$now = time();
for ($cnt = $nBack-1; $cnt >= 0; $cnt--) {
  $date = $cnt == 0 ? "Today" : strftime("%m/%d", $now - $cnt * 86400);
  $thead1 .= "<th>$date</th>";
  $tfoot0 .= "<th>$date</th>";
}
$tfoot0 .= "<th rowspan='2'>Station</th>"
	. "<th rowspan='2'>Program</th>";
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

foreach ($stations as $sensor => $name) {
  echo "<tr>\n";
  for ($j = $nBack-1; $j >= 0; $j--) {
    echo "<td>";
    if (array_key_exists($sensor, $past) and array_key_exists(-$j, $past[$sensor])) {
      echo mkRt($past[$sensor][-$j]);
    }
    echo "</td>\n";
  }
  echo "<th>$name</th>\n";
  echo "<th>";
  if (array_key_exists($sensor, $sens2pgm)) {echo implode(",", $sens2pgm[$sensor]);}
  echo "</th>";
  for ($j = 0; $j < $nFwd; $j++) {
    echo "<td>";
    if (array_key_exists($sensor, $future) and array_key_exists($j, $future[$sensor])) {
      echo mkRt($future[$sensor][$j]);
    }
    echo "</td>\n";
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
