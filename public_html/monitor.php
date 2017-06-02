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

if (!empty($_POST)) {
	if (array_key_exists('clearAll', $_POST)) {
		$cmdDB->clearAll();
	} elseif (array_key_exists('allOff', $_POST)) {
		$cmdDB->turnAllOff();
	} elseif (array_key_exists('off', $_POST)) {
		$cmdDB->offNow($_POST['idOff']);
	} elseif (array_key_exists('delete', $_POST)) {
		$cmdDB->offNow($_POST['idOn']);
		$cmdDB->offNow($_POST['idOff']);
	} elseif (array_key_exists('on', $_POST)) {
		$cmdDB->turnOnNow($_POST['id']);
	}
}

function vName($valve) {
	global $station, $masterValve;
	if (array_key_exists($valve, $station)) { return $station[$valve]; } 
	if (array_key_exists($valve, $masterValve)) { return $masterValve[$valve]; }
	return "Station $valve";
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

function mkPast(array $pgm) {
	global $cmdDB;
	$results = $cmdDB->query("SELECT * FROM onOffHistorical ORDER BY tOn DESC,addr LIMIT 50;");
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
		echo "<tr>\n<th>" . vName($row['addr'])
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['tOn'])
			. "</td>\n<td>" . mkRT($row['tOn'], $row['tOff'])
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n<td>" . $row['pre']
			. "</td>\n<td>" . $row['peak']
			. "</td>\n<td>" . $row['post']
			. "</td>\n<td>" . $row['codeOn']
			. "</td>\n<td>" . $row['codeOff']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkCurrent(array $pgm) {
	global $cmdDB;
	$now = time();
	$results = $cmdDB->query('SELECT addr,idOn,idOff,tOn,tOff,program,pre,peak,post,codeOn FROM onOffActive ' 
			. ' ORDER BY tOn,addr;');
	$hdr = "<tr><th></th><th>Station</th><th>Start</th>"
		. "<th>RunTime</th><th>Time Left</th><th>Pgm</th>"
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
			. "<input type='hidden' name='idOff' value='" . $row['idOff'] . "'>\n"
			. "<input type='submit' name='off' value='Off'>\n"
			. "</form>\n"
			. "</td>\n<th>" . vName($row['addr'])
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['tOn'])
			. "</td>\n<td>" . mkRT($row['tOn'], $now)
			. "</td>\n<td>" . mkRT($now, $row['tOff'])
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n<td>" . $row['pre']
			. "</td>\n<td>" . $row['peak']
			. "</td>\n<td>" . $row['post']
			. "</td>\n<td>" . $row['codeOn']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkPending(array $pgm) {
	global $cmdDB;
	$results = $cmdDB->query('SELECT * FROM onOffPending ORDER BY tOn,addr;');
	$hdr = "<tr><th></th><th>Station</th><th>Start</th>"
		. "<th>RunTime</th><th>Pgm</th></tr>";
	$qFirst = true;
	while ($row = $results->fetchArray()) {
		if ($qFirst) {
			$qFirst = false;
			echo "<hr>\n<h2>Pending</h2>\n";
			echo "<center>\n<table>\n";
			echo "<thead>$hdr</thead>\n<tbody>\n";
		}
		$valve = $row['addr'];
		echo "<tr>\n<td>\n"
			. "<form method='post'>\n"
			. "<input type='hidden' name='idOn' value='" . $row['idOn'] . "'>\n"
			. "<input type='hidden' name='idOff' value='" . $row['idOff'] . "'>\n"
			. "<input type='submit' name='delete' value='Delete'>\n"
			. "</form>\n"
			. "</td>\n<th>" . vName($valve)
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['tOn'])
			. "</td>\n<td>" . mkRT($row['tOn'], $row['tOff'])
			. "</td>\n<td>" . xlat($row['program'], $pgm)
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

$pgm = $parDB->loadTable("program", "id", "name");
$station = $parDB->loadTable("station INNER JOIN sensor ON station.sensor==sensor.id", 
			"sensor.addr", "station.name");
$masterValve = $parDB->loadTable("pocMV INNER JOIN sensor ON pocMV.sensor==sensor.id", 
			"sensor.addr", "pocMV.name");

echo "<table>\n<tr>\n";
echo "<td><form><input type='button' onclick='history.go(0)' value='Refresh'></form></td>\n";
echo "<td><form method='post'><input type='submit' name='clearAll' value='Clear All'></form></td>\n";
echo "<td><form method='post'>\n";
echo "<input type='hidden' name='id' value='255'>\n";
echo "<input type='hidden' name='pgm' value='-1'>\n";
echo "<input type='submit' name='allOff' value='All Off'>\n";
echo "</form></td>\n";

foreach ($masterValve as $key => $value) {
	echo "<td><form method='post'>";
	echo "<input type='hidden' name='id' value='$key'>\n";
        echo "<input type='hidden' name='pgm' value='-1'>\n";
	echo "<input type='submit' name='on' value='$value'>\n";
	echo "</form></td>\n";
}
echo "</tr>\n</table>\n";
mkCurrent($pgm);
mkPending($pgm);
mkPast($pgm);
?>
</body>
</html> 
