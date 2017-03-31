<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');

require_once 'php/CmdDB.php';

$tLimit = time() - 3600;

# Pick up current/voltage
$msg = 'data: {"curr":[';
$a = $cmdDB->query('SELECT timestamp,volts,mAmps FROM currentLog '
	. "WHERE timeStamp>$tLimit ORDER BY timeStamp DESC LIMIT 1;");
if ($row = $a->fetchArray()) {
	$msg .= $row[0] . ',' . $row[1] . ',' . $row[2];
	$qFirst = false;
}

$msg .= '],"sensor":[';

# Get sensors
$a = $cmdDB->query('SELECT timestamp,addr,value FROM sensorLog '
	. " WHERE timestamp>$tLimit GROUP BY addr ORDER BY addr;");
$cnt = 0;
while ($row = $a->fetchArray()) {
	if ($cnt++ != 0) { $msg .= ','; }
	$msg .= '[' . $row[0] . ',' . $row[1] . ',' . $row[2] . ']';
}

$msg .= '],"nOn":';

$n = $cmdDB->querySingle('SELECT count(DISTINCT addr) FROM onOffActive;');
$msg .= is_null($n) ? 0 : $n;
$msg .= ',"nPend":';
$n = $cmdDB->querySingle('SELECT count(DISTINCT addr) FROM onOffPending;');
$msg .= is_null($n) ? 0 : $n;
$msg .= "}\n\n";
echo $msg;
flush();
?>
