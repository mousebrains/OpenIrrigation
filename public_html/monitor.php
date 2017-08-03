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
		. " WHERE id=$1 AND cmdOn IS NOT NULL AND cmdOff IS NOT NULL;", [$_POST['id']]);
      $db->execute("UPDATE action SET tOff=CURRENT_TIMESTAMP"
		. " WHERE id=$1 AND cmdOn IS NULL AND cmdOff IS NOT NULL;", [$_POST['id']]);
    } elseif (array_key_exists('MVon', $_POST)) {
      $db->execute("UPDATE action SET tOff=CURRENT_TIMESTAMP"
		. " WHERE cmdOn IS NULL AND cmdOff IS NOT NULL;");
      $db->execute("INSERT INTO action(sensor,cmd,tOn,tOff,program,pgmDate) VALUES"
		. " ($1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+INTERVAL '10 HOURS',"
		. "getManualId(),CURRENT_DATE);",
		[$_POST['id']]);
    } elseif (array_key_exists('MVoff', $_POST)) {
      $db->execute("DELETE FROM action"
		. " WHERE sensor=$1 AND cmdOn IS NOT NULL AND cmdOff IS NOT NULL;", [$_POST['id']]);
      $db->execute("UPDATE action SET tOff=CURRENT_TIMESTAMP"
		. " WHERE sensor=$1 AND cmdOn IS NULL AND cmdOff IS NOT NULL;", [$_POST['id']]);
    }
    $db->commit();
  } catch (Exception $e) {
    echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
    $db->rollback();
  }
}

function loadAction($db, string $sql) {
  $results = $db->execute($sql);
  $a = [];
  while ($row = $results->fetchArray()) {
    array_push($a, $row);
  }
  return $a;
}

function loadActive($db) {
  $sql = "SELECT active.id"
	. ",date_trunc('seconds',(CAST(tOn AS TIME))) AS t"
	. ",date_trunc('seconds',CURRENT_TIMESTAMP-tOn) AS dtDone"
	. ",date_trunc('seconds',tOff-CURRENT_TIMESTAMP) AS dtLeft"
	. ",active.sensor,program,onCode,pre,peak,post"
	. " FROM active"
	. " ORDER BY tOn,sensor;";
  return loadAction($db, $sql);
}

function loadPending($db) {
  $sql = "SELECT id,sensor,program"
	. ",date_trunc('seconds',tOn) AS tOn"
	. ",date_trunc('seconds',tOff-tOn) AS dt"
	. " FROM pending"
	. " ORDER BY tOn,sensor;";
  return loadAction($db, $sql);
}

function mkRT(string $stime, string $etime = NULL) {
	if (is_null($stime) or is_null($etime)) { return ''; }
	$dt = strtotime($etime) - strtotime($stime);
	if ($dt < 3600) {return sprintf('%d:%02d', floor($dt / 60), $dt % 60);}
	return sprintf('%d:%02d:%02d', floor($dt / 3600), floor(($dt % 3600) / 60), $dt % 60);
}
	
function xlat($key, array $tbl) {
  return array_key_exists($key, $tbl) ? $tbl[$key] : $key;
}

function mkPast($db, array $pgm, array $sens2name) {
	$results = $db->execute("SELECT"
			. " date_trunc('seconds',tOn) AS tOn"
			. ",date_trunc('seconds',tOff-tOn) AS dt"
			. ",historical.sensor,program"
			. ",onCode,pre,peak,post"
			. ",offCode"
			. " FROM historical"
			. " ORDER BY tOn DESC,sensor"
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
		echo "<tr>\n<th>" . xlat($row['sensor'], $sens2name)
			. "</th>\n<td>" . $row['ton']
			. "</td>\n<td>" . $row['dt']
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n<td>" . $row['pre']
			. "</td>\n<td>" . $row['peak']
			. "</td>\n<td>" . $row['post']
			. "</td>\n<td>" . $row['oncode']
			. "</td>\n<td>" . $row['offcode']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkCurrent(array $rows, array $pgm, array $sens2name) {
	$hdr = "<tr><th></th><th>Station</th><th>Start</th>"
		. "<th>RunTime</th><th>Time Left</th><th>Program</th>"
		. "<th>Pre</th><th>Peak</th><th>Post</th><th>On Code</th></tr>";
	$qFirst = true;
	foreach ($rows as $row) {
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
			. "</td>\n<th>" . xlat($row['sensor'], $sens2name)
			. "</th>\n<td>" . $row['t']
			. "</td>\n<td>" . $row['dtdone']
			. "</td>\n<td>" . $row['dtleft']
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n<td>" . $row['pre']
			. "</td>\n<td>" . $row['peak']
			. "</td>\n<td>" . $row['post']
			. "</td>\n<td>" . $row['oncode']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkPending(array $rows, array $pgm, array $sens2name) {
	$hdr = "<tr><th></th><th>Station</th><th>Start</th>"
		. "<th>RunTime</th><th>Program</th></tr>";
	$qFirst = true;
	foreach ($rows as $row) {
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
			. "</td>\n<th>" . xlat($row['sensor'], $sens2name)
			. "</th>\n<td>" . $row['ton']
			. "</td>\n<td>" . $row['dt']
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkMaster(array $active, array $masterValve) {
  $q = [];
  foreach ($active as $entry) { $q[$entry['id']] = True; }

  foreach ($masterValve as $key => $value) {
    echo "<td><form method='post'>";
    echo "<input type='hidden' name='id' value='$key'>\n";
    if (array_key_exists($key, $q)) {
      echo "<input type='submit' name='MVoff' value='$value Off' style='background_color:red'>\n";
    } else {
      echo "<input type='submit' name='MVon' value='$value On'>\n";
    }
    echo "</form></td>\n";
  }
}

try {
  $pgm = $db->loadKeyValue("SELECT id,name FROM program ORDER BY name;");
  $masterValve = $db->loadKeyValue("SELECT sensor,name FROM pocMV ORDER BY name;");
  $stations = $db->loadKeyValue("SELECT sensor,name FROM station ORDER BY name;");
  $sens2name = [];
  foreach ($masterValve as $key => $value) $sens2name[$key] = $value;
  foreach ($stations as $key => $value) $sens2name[$key] = $value;

  $active = loadActive($db);
  $pending = loadPending($db);

  echo "<table>\n<tr>\n";
  echo "<td><form method='post'><input type='submit' value='Refresh'></form></td>\n";
  echo "<td><form method='post'><input type='submit' name='clearAll' value='Clear All'></form></td>\n";
  echo "<td><form method='post'>\n";
  echo "<input type='hidden' name='id' value='255'>\n";
  echo "<input type='submit' name='allOff' value='All Off'>\n";
  echo "</form></td>\n";

  mkMaster($active, $masterValve);
  echo "</tr>\n</table>\n";
  mkCurrent($active, $pgm, $sens2name);
  mkPending($pending, $pgm, $sens2name);
  mkPast($db, $pgm, $sens2name);
} catch (Exception $e) {
  echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
}
?>
</body>
</html> 
