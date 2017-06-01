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

$stn = [];
$results = $parDB->query('SELECT station.id,sensor.addr FROM sensor INNER JOIN station ON sensor.id==station.sensor;');
while ($row = $results->fetchArray()) {
  $stn[$row[1]] = $row[0];
}

$now = time();

$msg = procSQL(NULL, $cmdDB, "Active", "SELECT addr,tOff-$now FROM onOffActive;", $stn);
$msg = procSQL(NULL, $cmdDB, "pActive", "SELECT addr,$now-tOn FROM onOffActive;", $stn);
$msg = procSQL($msg, $parDB, "Sched", "SELECT station,runTime FROM pgmStn"
	. " INNER JOIN program ON pgmStn.program==program.id AND program.name=='Manual';",
	[]);
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

echo "data: {{$msg}}\n\n";
flush();
?>
