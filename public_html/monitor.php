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

if (!empty($_POST)) {
echo "<pre>";
var_dump($_POST);
echo "</pre>";
  try {
    $db->begin();
    if (array_key_exists('clearAll', $_POST)) {
      $db->execute("DELETE FROM action WHERE cmdOn IS NOT NULL AND cmdOff IS NOT NULL;");
      $db->execute("UPDATE action SET tOff=CURRENT_TIMESTAMP"
		. " WHERE cmdOn IS NULL AND cmdOff IS NOT NULL;");
    } elseif (array_key_exists('allOff', $_POST)) {
      $db->execute("UPDATE action SET tOff=CURRENT_TIMESTAMP"
		. " WHERE cmdOn IS NULL AND cmdOff IS NOT NULL;");
    } elseif (array_key_exists('off', $_POST)) {
      $db->execute("UPDATE action SET tOFF=CURRENT_TIMESTAMP"
		. " WHERE id=$1 AND cmdOff IS NOT NULL;", [$_POST['id']]);
    } elseif (array_key_exists('delete', $_POST)) {
      $db->execute("DELETE FROM action"
		. " WHERE id=$1 AND cmdOn IS NOT NULL AND cmdOff IS NOT NULL;", $_POST['id']);
      $db->execute("UPDATE action SET tOff=CURRENT_TIMESTAMP"
		. " WHERE id=$1 AND cmdOn IS NULL AND cmdOff IS NOT NULL;", $_POST['id']);
    } elseif (array_key_exists('MVon', $_POST)) {
      echo "<div><h1>Master Valve Operations are not currently supported</h1></div>\n"; 
      // $db->execute("INSERT INTO action(uUPDATE action SET tOn=CURRENT_TIMESTAMP"
		// . " WHERE id=$1 AND cmdOn IS NOT NULL AND cmdOff IS NOT NULL;", $_POST['id']);
    }
    $db->commit();
  } catch (Exception $e) {
    echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
    $db->rollback();
  }
}

function mkRT(int $stime, int $etime = NULL) {
	if (is_null($stime) or is_null($etime)) { return ''; }
	$dt = $etime - $stime;
	if ($dt < 3600) {return sprintf('%d:%02d', floor($dt / 60), $dt % 60);}
	return sprintf('%d:%02d:%02d', floor($dt / 3600), floor(($dt % 3600) / 60), $dt % 60);
}
	
function xlat($key, array $tbl) {
  return array_key_exists($key, $tbl) ? $tbl[$key] : $key;
}

function mkPast($db, array $pgm, array $station) {
	$results = $db->execute("SELECT historical.id,tOn,tOff,station,program,"
			. "onLog.code AS codeOn,pre,peak,post,"
			. "offLog.code AS codeOff"
			. " FROM historical"
			. " INNER JOIN onLog ON onLog=onLog.id"
			. " INNER JOIN offLog ON offLog=offLog.id"
			. " ORDER BY tOn DESC,station"
			. " LIMIT 100;");
	$hdr = "<tr><th>Station</th><th>Start</th><th>RunTime</th><th>Program</th><th>Pre</th><th>Peak</th>"
		. "<th>Post</th><th>On Code</th><th>Off Code</th></tr>";
	$qFirst = true;
	while ($row = $results->fetchArray()) {
		if ($qFirst) {
			$qFirst = false;
			echo "<hr>\n<h2>Past</h2>\n";
			echo "<center>\n<table>\n";
			echo "<thead>$hdr</thead>\n<tbody>\n";
		}
		echo "<tr>\n<th>" . xlat($row['station'], $station)
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['ton'])
			. "</td>\n<td>" . mkRT($row['ton'], $row['toff'])
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n<td>" . $row['pre']
			. "</td>\n<td>" . $row['peak']
			. "</td>\n<td>" . $row['post']
			. "</td>\n<td>" . $row['codeon']
			. "</td>\n<td>" . $row['codeoff']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkCurrent($db, array $pgm, array $station) {
	$now = time();
	$results = $db->execute("SELECT active.id,tOn,tOff,station,program,code,pre,peak,post"
			. " FROM active"
			. " INNER JOIN onLOG ON onLog=onLog.id" 
			. " ORDER BY tOn,station;");
	$hdr = "<tr><th></th><th>Station</th><th>Start</th>"
		. "<th>RunTime</th><th>Time Left</th><th>Program</th>"
		. "<th>Pre</th><th>Peak</th><th>Post</th><th>On Code</th></tr>";
	$qFirst = true;
	while ($row = $results->fetchArray()) {
		if ($qFirst) {
			$qFirst = false;
			echo "<center>\n<table>\n";
			echo "<thead>$hdr</thead>\n<tbody>\n";
		}
		echo "<tr>\n<td>\n"
			. "<form method='post'>\n"
			. "<input type='hidden' name='id' value='" . $row['id'] . "'>\n"
			. "<input type='submit' name='off' value='Off'>\n"
			. "</form>\n"
			. "</td>\n<th>" . xlat($row['station'], $station)
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['ton'])
			. "</td>\n<td>" . mkRT($row['ton'], $now)
			. "</td>\n<td>" . mkRT($now, $row['toff'])
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n<td>" . $row['pre']
			. "</td>\n<td>" . $row['peak']
			. "</td>\n<td>" . $row['post']
			. "</td>\n<td>" . $row['code']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkPending($db, array $pgm, array $station) {
	$results = $db->execute("SELECT id,tOn,tOff,station,program"
			. " FROM pending"
			. " ORDER BY tOn,station;");
	$hdr = "<tr><th></th><th>Station</th><th>Start</th>"
		. "<th>RunTime</th><th>Program</th></tr>";
	$qFirst = true;
	while ($row = $results->fetchArray()) {
		if ($qFirst) {
			$qFirst = false;
			echo "<hr>\n<h2>Pending</h2>\n";
			echo "<center>\n<table>\n";
			echo "<thead>$hdr</thead>\n<tbody>\n";
		}
		echo "<tr>\n<td>\n"
			. "<form method='post'>\n"
			. "<input type='hidden' name='id' value='" . $row['id'] . "'>\n"
			. "<input type='submit' name='delete' value='Delete'>\n"
			. "</form>\n"
			. "</td>\n<th>" . xlate($row['station'], $station)
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['ton'])
			. "</td>\n<td>" . mkRT($row['ton'], $row['toff'])
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

try {
  $pgm = $db->loadKeyValue("SELECT id,name FROM program ORDER BY name;");
  $station = $db->loadKeyValue("SELECT id,name FROM station ORDER BY name;");
  $masterValve = $db->loadKeyValue("SELECT id,name FROM pocMV ORDER BY name;");

  echo "<table>\n<tr>\n";
  echo "<td><form><input type='button' onclick='history.go(0)' value='Refresh'></form></td>\n";
  echo "<td><form method='post'><input type='submit' name='clearAll' value='Clear All'></form></td>\n";
  echo "<td><form method='post'>\n";
  echo "<input type='hidden' name='id' value='255'>\n";
  echo "<input type='submit' name='allOff' value='All Off'>\n";
  echo "</form></td>\n";

  foreach ($masterValve as $key => $value) {
	  echo "<td><form method='post'>";
	  echo "<input type='hidden' name='id' value='$key'>\n";
	  echo "<input type='submit' name='MVon' value='$value'>\n";
	  echo "</form></td>\n";
  }
  echo "</tr>\n</table>\n";
  mkCurrent($db, $pgm, $station);
  mkPending($db, $pgm, $station);
  mkPast($db, $pgm, $station);
} catch (Exception $e) {
  echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
}
?>
</body>
</html> 
