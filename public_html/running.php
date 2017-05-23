<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');

require_once 'php/CmdDB.php';

function procSQL($msg, $db, $suffix, $sql) {
  $dt = NULL;
  $results = $db->query($sql);
  while ($row = $results->fetchArray()) {
    $addr = $row[0];
    if (!is_null($dt)) { $dt .= ","; }
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

$now = time();

$msg = procSQL(NULL, $cmdDB, "Active", "SELECT addr,tOff-$now FROM onOffActive;");
$msg = procSQL($msg, $cmdDB, "Pending", 
	"SELECT addr,sum(tOff-tOn)"
        . " FROM onOffPending"
        . " WHERE tOn <= " . ($now + 86400)
        . " GROUP BY addr;");
$msg = procSQL($msg, $cmdDB, "Past", 
	"SELECT"
        . " addr,sum(tOff-max(tOn," . ($now-86400) . "))"
        . " FROM onOffHistorical"
        . " WHERE tOff >= " . ($now - 86400)
        . " GROUP BY addr;");

echo "data: {{$msg}}\n\n";
flush();
?>
