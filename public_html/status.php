<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');

require_once 'php/CmdDB.php';

# Pick up current/voltage
$msg = 'data: {"curr":[';
$a = $cmdDB->query('SELECT timestamp,volts,mAmps FROM currentLog ORDER BY timeStamp DESC LIMIT 1;');
if ($row = $a->fetchArray()) {
	$msg .= $row[0] . ',' . $row[1] . ',' . $row[2];
	$qFirst = false;
}

$msg .= '],"sensor":[';

# Get sensors
$a = $cmdDB->query('SELECT timestamp,sensor,val FROM sensorLog GROUP BY sensor ORDER BY sensor;');
$cnt = 0;
while ($row = $a->fetchArray()) {
	if ($cnt++ != 0) { $msg .= ','; }
	$msg .= '[' . $row[0] . ',' . $row[1] . ',' . $row[2] . ']';
}

$msg .= '],"onOff":[';

# Get on valves and finish time
$a = $cmdDB->query('SELECT onOffLog.valve,onTimeStamp,min(timestamp) FROM onOffLog INNER JOIN commands ON cmd==1 and offTimeStamp is NULL and onOffLog.valve==commands.valve GROUP BY onOffLog.valve;');
$cnt = 0;
while ($row = $a->fetchArray()) {
	if ($cnt++ != 0) { $msg .= ','; }
	$msg .= '[' . $row[0] . ',' . $row[1] . ',' . $row[2] . ']';
}

echo $msg . "]}\n\n";
flush();
?>
