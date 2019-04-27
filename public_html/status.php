<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

require_once 'php/DB.php';

class Query {
  private $nActive = NULL;
  private $nPend= NULL;
  private $tPrevMsg = NULL;

  function __construct($db) {
    $this->db = $db;
    $this->oneDay = new DateInterval("P0DT1H");
    $this->dt = new DateInterval("PT50S");
    $this->tPrev = (new DateTimeImmutable())->sub($this->oneDay);
    if (is_null($this->tPrevMsg)) {$this->tPrevMsg = $this->tPrev;}
    $this->controllers = $db->loadKeyValue("SELECT id,name FROM controller;");
    $this->sensors = $db->loadKeyValue("SELECT id,name FROM pocFlow;");
    $this->current = $db->prepare("SELECT DISTINCT ON (controller)"
		. " controller,timestamp,volts,mAmps FROM currentLog"
		. " WHERE timeStamp>=$1 ORDER BY controller,timeStamp DESC;");
    $this->sensor = $db->prepare("SELECT "
		. " pocFlow,timestamp,round(CAST(flow AS numeric),1) FROM sensorLog"
		. " WHERE timeStamp>=$1 ORDER BY timeStamp DESC LIMIT 10;");

    $this->nOn = $db->prepare("SELECT count(DISTINCT sensor) FROM active;");
    $this->nPending = $db->prepare("SELECT count(DISTINCT sensor) FROM pending WHERE tOn<=$1;");
    $this->prevCurrent = NULL;
    $this->prevSensor = NULL;
    $this->nActive = NULL;
    $this->nPend = NULL;
  }

  function sendIt() {
    $content = [];
    $tLimit = $this->tPrev->format("Y-m-d H:i:s");
    $now = new DateTimeImmutable();
    $a = $this->current->execute([$tLimit]);
    $current = [];
    while ($row = $a->fetchArray()) {
      $id = $row[0];
      if (array_key_exists($id, $this->controllers)) {
        $current[$id] = '["' . $this->controllers[$id] . '",' 
		      . strtotime($row[1]) . "," . $row[2] . "," . $row[3] . "]";
      }
    }
    if (!empty($current) and (($current != $this->prevCurrent) or is_null($this->prevCurrent))) {
      $this->prevCurrent = $current;
      array_push($content, '"curr":[' . implode(",", $current) . "]");
    }

    # Get sensors
    $a = $this->sensor->execute([$tLimit]);
    $sensor = [];
    while ($row = $a->fetchArray()) {
      $id = $row[0];
      if (array_key_exists($id, $this->sensors)) {
	$sensor[$id] = '["' . $this->sensors[$id] . '",' 
			    . strtotime($row[1]) . ',' . $row[2] . ']';
      }
    }
    if (!empty($sensor) and (($sensor != $this->prevSensor) or is_null($this->prevSensor))) {
      $this->prevSensor = $sensor;
      array_push($content, '"sensor":[' . implode(",", $sensor) . "]");
    }

    # Get number active
    $n = $this->nOn->querySingle();
    if (empty($n)) {$n = 0;}
    if (is_null($this->nActive) or ($n != $this->nActive)) {
      array_push($content, '"nOn":' . $n);
      $this->nActive = $n;
    }

    # Get number pending
    $n = $this->nPending->querySingle([$now->add($this->oneDay)->format('Y-m-d H:i:s')]);
    if (is_null($n)) {$n = 0;}
    if (is_null($this->nPend) or ($n != $this->nPend)) {
      array_push($content, '"nPend":' . $n);
      $this->nPend= $n;
    }

    if (!empty($content)) {
      echo "data: {" . implode(",", $content) . "}\n\n";
      if (ob_get_length()) {ob_flush();}  // Flush output buffer
      flush();
      $this->tPrevMsg = $now;
    } else if ($this->tPrevMsg->add($this->dt) < $now) { // Heartbeat
      echo "data: {}\n\n";
      if (ob_get_length()) {ob_flush();}  // Flush output buffer
      flush();
      $this->tPrevMsg = $now;
    }

    $this->tPrev = $now;
  }
}

$query = new Query($db);

while (True) {
  $query->sendIt();
  sleep(1);
}
?>
