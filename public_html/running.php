<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

require_once 'php/DB.php';

class Query {
  private $tBack;
  private $tFwd;
  private $dt;
  private $tPrevMsg;
  private $previous = NULL;

  function __construct($db) {
    $this->tBack = new DateInterval("P1D");
    $this->tFwd  = new DateInterval("P1D");
    $this->dt    = new DateInterval("PT50S");
    $this->tPrevMsg = new DateTimeImmutable();
    $this->active = $db->prepare("SELECT sensor,"
		. "round(date_part('epoch',min(tOff)-$1)),"
		. "round(date_part('epoch',$1-min(tOn)))"
		. " FROM active"
		. " GROUP BY sensor;");
    $this->past = $db->prepare("SELECT sensor,round(date_part('epoch',sum(tOff-tOn)))"
		. " FROM historical"
		. " WHERE tOff>=$1"
		. " GROUP BY sensor;");
    $this->pend = $db->prepare("SELECT sensor,round(date_part('epoch',sum(tOff-tOn)))"
		. " FROM pending"
		. " WHERE tOn<=$1"
		. " GROUP BY sensor;");
    $this->sched = $db->prepare("SELECT station.sensor,sum(runTime)*60"
		. " FROM pgmStn"
		. " INNER JOIN station"
		. " ON qSingle=True"
		. " AND pgmStn.station=station.id"
		. " GROUP BY station.sensor;");
  }

  function sendIt() {
    $format = 'Y-m-d H:i:s';
    $now = new DateTimeImmutable();
    $msg = [];

    {
      $fActive = [];
      $pActive = [];
      $results = $this->active->execute([$now->format($format)]);
      while ($row = $results->fetchRow()) {
        $sensor = $row[0];
        array_push($fActive, '"' . $sensor . '":' . $row[1]);
        array_push($pActive, '"' . $sensor . '":' . $row[2]);
      }
      if (!empty($fActive)) {
        array_push($msg, '"dtActive":{' . implode(",", $fActive) . '}');
        array_push($msg, '"dtpActive":{' . implode(",", $pActive) . '}');
     }
    }

    {
      $pending = [];
      $tLimit = $now->add($this->tFwd);
      $results = $this->pend->execute([$now->add($this->tFwd)->format($format)]);
      while ($row = $results->fetchRow()) {array_push($pending, '"' . $row[0] . '":' . $row[1]);}
      if (!empty($pending)) {array_push($msg, '"dtPending":{' . implode(",", $pending) . '}');}
    }

    {
      $past = [];
      $results = $this->past->execute([$now->sub($this->tBack)->format($format)]);
      while ($row = $results->fetchArray()) {array_push($past, '"' . $row[0] . '":' . $row[1]);}
      if (!empty($past)) {array_push($msg, '"dtPast":{' . implode(",", $past) . '}');}
    }

    {
    $sched = [];
      $results = $this->sched->execute();
      while ($row = $results->fetchArray()) {array_push($sched, '"' . $row[0] . '":' . $row[1]);}
      if (!empty($sched)) {array_push($msg, '"dtSched":{' . implode(",", $sched) . '}');}
    }

    // There is a 60 second timeout in NGINX, so generate a new message at least every ~50 seconds
    if ((!empty($msg) and ($msg != $this->previous)) or ($this->tPrevMsg->add($this->dt) < $now)) {
      $this->previous = $msg;
      echo "data: {" . implode(",", $msg) . "}\n\n";
      if (ob_get_length()) {ob_flush();} // Flush output buffer
      flush();
      $this->tPrevMsg = $now;
    }
  }
}

$query = new Query($db);

while (True) {
  $query->sendIt();
  sleep(1);
}
?>
