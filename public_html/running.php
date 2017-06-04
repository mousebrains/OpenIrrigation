<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');

require_once 'php/CmdDB.php';
require_once 'php/ParDB.php';

function procSQL($msg, $db, string $suffix, string $sql, array $stn) {
  $dt = NULL;
  $results = $db->query($sql);
  while ($row = $results->fetchArray()) {
    $addr = $row[0];
    if (!is_null($dt)) { $dt .= ","; }
    if (array_key_exists($addr, $stn)) { $addr = $stn[$addr]; }
    $dt .= "\"$addr\":" . $row[1];
  }
  if (is_null($dt)) {return $msg;}
  if (is_null($msg)) {
    $msg = "";
  } else {
    $msg .= ",";
  }
  return $msg . "\"dt$suffix\":{{$dt}}";
}

$stn = $parDB->loadKeyValue('SELECT sensor.addr,station.id'
		. ' FROM sensor INNER JOIN station ON sensor.id==station.sensor;');
$done = $cmdDB->loadColumn('SELECT pgmStn FROM pgmStnTbl;');
 
$now = time();

$msg = procSQL(NULL, $cmdDB, "Active", "SELECT addr,tOff-$now FROM onOffActive;", $stn);
$msg = procSQL($msg, $cmdDB, "pActive", "SELECT addr,$now-tOn FROM onOffActive;", $stn);
$msg = procSQL($msg, $cmdDB, "Pending", 
	"SELECT addr,sum(tOff-tOn)"
        . " FROM onOffPending"
        . " WHERE tOn <= " . ($now + 86400)
        . " GROUP BY addr;",
	$stn);
$msg = procSQL($msg, $cmdDB, "Past", 
	"SELECT"
        . " addr,sum(tOff-max(tOn," . ($now-86400) . "))"
        . " FROM onOffHistorical"
        . " WHERE tOff >= " . ($now - 86400)
        . " GROUP BY addr;",
	$stn);

$sql = "SELECT station,runtime FROM pgmStn WHERE qSingle==1";
if (!empty($done)) {$sql .= " AND id NOT IN(" . implode($done, ",") . ")";}
$msg = procSQL($msg, $parDB, "Sched", $sql . ";", []);

echo "data: {{$msg}}\n\n";
flush();
?>
