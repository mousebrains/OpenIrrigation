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
	// echo "<pre>\n";
	// var_dump($_POST);
	// echo "</pre>\n";
	if (array_key_exists('clearAll', $_POST)) {
		$cmdDB->exec('DELETE FROM commands;');
		$cmdDB->exec('INSERT INTO commands (valve,cmd,timestamp)'
			. ' VALUES(255,1,CURRENT_TIMESTAMP);'); 
	} elseif (array_key_exists('off', $_POST)) {
		$stmt = $cmdDB->prepare('INSERT INTO commands (timestamp,valve,cmd) VALUES('
				. ':time,:id,1);');
		$stmt->bindValue(':time', time());
		$stmt->bindValue(':id', $_POST['id']);
		$stmt->execute();
		$stmt->close();
	} elseif (array_key_exists('delete', $_POST)) {
		$stmt = $cmdDB->prepare('DELETE FROM commands WHERE id==:aid OR id==:bid;');
		$stmt->bindValue(':aid', $_POST['aid']);
		$stmt->bindValue(':bid', $_POST['bid']);
		$stmt->execute();
		$stmt->close();
	} elseif (array_key_exists('on', $_POST)) {
		$stmt = $cmdDB->prepare('INSERT INTO commands (timestamp,valve,cmd) VALUES('
				. ':time,:id,0);');
		$stmt->bindValue(':time', time());
		$stmt->bindValue(':id', $_POST['id']);
		$stmt->execute();
		$stmt->close();
	}
}

function vName($valve) {
	global $station, $masterValve;
	if (array_key_exists($valve, $station)) { return $station[$valve]; } 
	if (array_key_exists($valve, $masterValve)) { return $masterValve[$valve]; }
	return "Station $valve";
}

function mkRT(int $stime, int $etime) {
	$dt = $etime - $stime;
	if ($dt < 3600) {return sprintf('%d:%02d', floor($dt / 60), $dt % 60);}
	return sprintf('%d:%02d:%02d', floor($dt / 3600), floor(($dt % 3600) / 60), $dt % 60);
}
	

function mkPast() {
	global $cmdDB;
	$results = $cmdDB->query("SELECT * FROM onOffLog WHERE offTimeStamp IS NOT NULL" .
				" ORDER BY onTimeStamp DESC,valve ASC LIMIT 500;");
	$hdr = "<tr><th>Station</th><th>Start</th><th>RunTime</th><th>Pre</th><th>Peak</th>"
		. "<th>Post</th><th>On Code</th><th>Off Code</th></tr>";
	$qFirst = true;
	while ($row = $results->fetchArray()) {
		if ($qFirst) {
			$qFirst = false;
			echo "<hr>\n<h2>Past</h2>\n";
			echo "<center>\n<table>\n";
			echo "<thead>$hdr</thead>\n<tbody>\n";
		}
		echo "<tr>\n<th>" . vName($row['valve'])
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['onTimeStamp'])
			. "</td>\n<td>" . mkRT($row['onTimeStamp'], $row['offTimeStamp'])
			. "</td>\n<td>" . $row['preCurrent']
			. "</td>\n<td>" . $row['peakCurrent']
			. "</td>\n<td>" . $row['postCurrent']
			. "</td>\n<td>" . $row['onCode']
			. "</td>\n<td>" . $row['offCode']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkCurrent() {
	global $cmdDB;
	$now = time();
	$results = $cmdDB->query('SELECT'
		. ' onOffLog.valve,onTimeStamp,min(timestamp) as timestamp,'
		. 'preCurrent,peakCurrent,postCurrent,onCode'
		. ' FROM onOffLog'
		. ' INNER JOIN commands'
		. ' ON ((onOffLog.valve==commands.valve) OR (commands.valve==255))'
		. ' AND offTimeStamp is NULL'
		. ' AND cmd == 1'
		. ' GROUP BY onTimeStamp, onOffLog.valve;'); 
	$hdr = "<tr><th></th><th>Station</th><th>Start</th>"
		. "<th>RunTime</th><th>Time Left</th>"
		. "<th>Pre</th><th>Peak</th><th>Post</th><th>On Code</th></tr>";
	$qFirst = true;
	while ($row = $results->fetchArray()) {
		if ($qFirst) {
			$qFirst = false;
			echo "<center>\n<table>\n";
			echo "<thead>$hdr</thead>\n<tbody>\n";
		}
		$valve = $row['valve'];
		echo "<tr>\n<td>\n"
			. "<form method='post'>\n"
			. "<input type='hidden' name='id' value='$valve'>\n"
			. "<input type='submit' name='off' value='Off'>\n"
			. "</form>\n"
			. "</td>\n<th>" . vName($valve)
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['onTimeStamp'])
			. "</td>\n<td>" . mkRT($row['onTimeStamp'], $now)
			. "</td>\n<td>" . mkRT($now, $row['timestamp'])
			. "</td>\n<td>" . $row['preCurrent']
			. "</td>\n<td>" . $row['peakCurrent']
			. "</td>\n<td>" . $row['postCurrent']
			. "</td>\n<td>" . $row['onCode']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

function mkPending() {
	global $cmdDB;
	$results = $cmdDB->query('SELECT'
		. ' A.valve,A.timestamp as tOn,min(B.timestamp) AS tOff,A.src'
		. ',A.id AS aid,B.id AS bid'
		. ' FROM commands AS A'
		. ' INNER JOIN commands AS B'
		. ' ON ((A.valve==B.valve) OR (B.valve==255))'
		. ' AND A.cmd == 0'
		. ' AND B.cmd == 1'
		. ' AND A.timestamp <= B.timestamp'
		. ' GROUP BY A.timestamp,A.valve'
		. ' ORDER BY A.timestamp,A.valve;');
	$hdr = "<tr><th></th><th>Station</th><th>Start</th>"
		. "<th>RunTime</th><th>Source</th></tr>";
	$qFirst = true;
	while ($row = $results->fetchArray()) {
		if ($qFirst) {
			$qFirst = false;
			echo "<hr>\n<h2>Pending</h2>\n";
			echo "<center>\n<table>\n";
			echo "<thead>$hdr</thead>\n<tbody>\n";
		}
		$valve = $row['valve'];
		echo "<tr>\n<td>\n"
			. "<form method='post'>\n"
			. "<input type='hidden' name='aid' value='" . $row['aid'] . "'>\n"
			. "<input type='hidden' name='bid' value='" . $row['bid'] . "'>\n"
			. "<input type='submit' name='delete' value='Delete'>\n"
			. "</form>\n"
			. "</td>\n<th>" . vName($valve)
			. "</th>\n<td>" . strftime('%m/%d %H:%M:%S', $row['tOn'])
			. "</td>\n<td>" . mkRT($row['tOn'], $row['tOff'])
			. "</td>\n<td>" . $row['src']
			. "</td>\n</tr>\n";
	}
	if (!$qFirst) {
		echo "</tbody>\n<tfoot>$hdr</tfoot>\n</table>\n</center>\n";
	}
}

$station = $parDB->loadTable("station INNER JOIN sensor ON station.sensor==sensor.id", 
			"sensor.addr", "station.name");
$masterValve = $parDB->loadTable("pocMV INNER JOIN sensor ON pocMV.sensor==sensor.id", 
			"sensor.addr", "pocMV.name");

echo "<table>\n<tr>\n";
echo "<td><form><input type='button' onclick='history.go(0)' value='Refresh'></form></td>\n";
echo "<td><form method='post'><input type='submit' name='clearAll' value='Clear All'></form></td>\n";
echo "<td><form method='post'>\n";
echo "<input type='hidden' name='id' value='255'>\n";
echo "<input type='submit' name='off' value='All Off'>\n";
echo "</form></td>\n";

foreach ($masterValve as $key => $value) {
	echo "<td><form method='post'>";
	echo "<input type='hidden' name='id' value='$key'>\n";
	echo "<input type='submit' name='on' value='$value'>\n";
	echo "</form></td>\n";
}
echo "</tr>\n</table>\n";
mkCurrent();
mkPending();
mkPast();
?>
</body>
</html> 
