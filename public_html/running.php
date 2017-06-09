<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

require_once 'php/CmdDB.php';
require_once 'php/ParDB.php';

class Query {
  private $tBack = 86400;
  private $tFwd = 86400;
  private $previous = NULL;
  private $tPrevMsg = 0;

  function __construct($cmdDB, $parDB) {
    $this->cmdDB = $cmdDB;
    $this->parDB = $parDB;
    $this->stn = $parDB->loadKeyValue('SELECT sensor.addr,station.id'
			. ' FROM sensor INNER JOIN station ON sensor.id==station.sensor;');
  }

  function sendIt() {
    $now = time();
    $msg = [];
    $fActive = [];
    $pActive = [];
    $pending = [];
    $past = [];
    $sched = [];

    $results = $this->cmdDB->query("SELECT addr,sum(tOff-$now),sum($now-tOn)"
		. " FROM onOffActive GROUP BY addr;");
    while ($row = $results->fetchArray()) {
      $addr = $row[0];
      if (array_key_exists($addr, $this->stn)) {
        $addr = $this->stn[$addr];
        array_push($fActive, '"' . $addr . '":' . $row[1]);
        array_push($pActive, '"' . $addr . '":' . $row[2]);
      }
    }
    if (!empty($fActive)) {
      array_push($msg, '"dtActive":{' . implode(",", $fActive) . '}');
      array_push($msg, '"dtpActive":{' . implode(",", $pActive) . '}');
    }

    $tLimit = $now + $this->tFwd;
    $results = $this->cmdDB->query("SELECT addr,sum(tOff-tOn) FROM onOffPending"
		. " WHERE tOn<=$tLimit GROUP BY addr;");
    while ($row = $results->fetchArray()) {
      $addr = $row[0];
      if (array_key_exists($addr, $this->stn)) {
        array_push($pending, '"' . $this->stn[$addr] . '":' . $row[1]);
      }
    }
    if (!empty($pending)) {array_push($msg, '"dtPending":{' . implode(",", $pending) . '}');}

    $tLimit = $now - $this->tBack;
    $results = $this->cmdDB->query("SELECT addr,sum(tOff-tOn) FROM onOffHistorical"
		. " WHERE tOff>=$tLimit GROUP BY addr;");
    while ($row = $results->fetchArray()) {
      $addr = $row[0];
      if (array_key_exists($addr, $this->stn)) {
        array_push($past, '"' . $this->stn[$addr] . '":' . $row[1]);
      }
    }
    if (!empty($past)) {array_push($msg, '"dtPast":{' . implode(",", $past) . '}');}

    $results = $this->parDB->query("SELECT station,sum(runtime) FROM pgmStn"
		. " WHERE qSingle==1 GROUP by station;");
    while ($row = $results->fetchArray()) {
      array_push($sched, '"' . $row[0] . '":' . $row[1]);
    }
    if (!empty($sched)) {array_push($msg, '"dtSched":{' . implode(",", $sched) . '}');}

    // There is a 60 second timeout in NGINX, so generate a new message at least every ~50 seconds
    if (!empty($msg) and (($msg != $this->previous) or (($this->tPrevMsg + 50) < $now))) {
      $this->previous = $msg;
      echo "data: {" . implode(",", $msg) . "}\n\n";
      if (ob_get_length()) {ob_flush();} // Flush output buffer
      flush();
      $this->tPrevMsg = $now;
    }
  }
}

$query = new Query($cmdDB, $parDB);

while (True) {
  $query->sendIt();
  sleep(1);
}
?>
