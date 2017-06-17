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
    $this->oneDay = new DateInterval("P1D");
    $this->dt = new DateInterval("PT50S");
    $this->tPrev = (new DateTimeImmutable())->sub($this->oneDay);
    if (is_null($this->tPrevMsg)) {$this->tPrevMsg = $this->tPrev;}
    $this->current = $db->prepare("SELECT timestamp,volts,mAmps FROM currentLog" 
		. " WHERE timeStamp>=$1 ORDER BY timeStamp DESC LIMIT 1;");
    $this->sensor = $db->prepare("SELECT timestamp,addr,value FROM sensorLog"
		. " WHERE (timestamp,addr) IN ("
		. "SELECT max(timestamp),addr FROM sensorLog"
		.	" WHERE timestamp>$1 GROUP BY addr"
		. ") ORDER BY addr;");

    $this->nOn = $db->prepare("SELECT count(DISTINCT station) FROM active;");
    $this->nPending = $db->prepare("SELECT count(DISTINCT station) FROM pending WHERE tOn<=$1;");
  }

  function sendIt() {
    $content = [];
    $tLimit = $this->tPrev->format("Y-m-d H:i:s");
    $now = new DateTimeImmutable();
    $a = $this->current->execute([$tLimit]);
    if ($row = $a->fetchArray()) {
      var_dump($row);
      $current = '"curr":[' . $row[0] . "," . $row[1] . "," . $row[2] . "]";
      if (is_null($this->current) or ($current != $this->current)) {
        $this->current = $current;
        array_push($content, $current);
      }
    }

    # Get sensors
    $a = $this->sensor->execute([$tLimit]);
    $sensor = [];
    while ($row = $a->fetchArray()) {
      var_dump($row);
      array_push($sensor, '[' . $row[0] . ',' . $row[1] . ',' . $row[2] . ']');
    }
    if (!empty($sensor) and (($sensor != $this->sensor) or is_null($this->sensor))) {
      $this->sensor = $sensor;
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

# while (True) {
  $query->sendIt();
  # sleep(1);
# }
?>
