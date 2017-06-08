<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

require_once 'php/CmdDB.php';

class Query {
  private $nActive = NULL;
  private $nPending = NULL;
  private $current = NULL;
  private $sensor = NULL;

  function __construct($db) {
    $this->db = $db;
    $this->tPrev = time() - 86400;
    ob_end_clean(); // Turn off output buffering
  }

  function sendIt() {
    $content = [];
    $tLimit = $this->tPrev;
    $db = $this->db;
    $now = time();
    $a = $db->query('SELECT timestamp,volts,mAmps FROM currentLog '
		. "WHERE timeStamp>=$tLimit ORDER BY timeStamp DESC LIMIT 1;");
    if ($row = $a->fetchArray()) {
      $current = '"curr":[' . $row[0] . "," . $row[1] . "," . $row[2] . "]";
      if (is_null($this->current) or ($current != $this->current)) {
        $this->current = $current;
        array_push($content, $current);
      }
    }

    # Get sensors
    $a = $db->query('SELECT timestamp,addr,value FROM sensorLog '
		. " WHERE timestamp>=$tLimit GROUP BY addr ORDER BY addr;");
    $sensor = [];
    while ($row = $a->fetchArray()) {
      array_push($sensor, '[' . $row[0] . ',' . $row[1] . ',' . $row[2] . ']');
    }
    if (!empty($sensor) and (($sensor != $this->sensor) or is_null($this->sensor))) {
      $this->sensor = $sensor;
      array_push($content, '"sensor":[' . implode(",", $sensor) . "]");
    }

    $n = $db->querySingle('SELECT count(DISTINCT addr) FROM onOffActive;');
    if (is_null($n)) {$n = 0;}
    if (is_null($this->nActive) or ($n != $this->nActive)) {
      array_push($content, '"nOn":' . $n);
      $this->nActive = $n;
    }

    $tLimit = $now + 86400; // Look forward one day for pending
    $n = $db->querySingle("SELECT count(DISTINCT addr) FROM onOffPending WHERE tOn<$tLimit;");
    if (is_null($n)) {$n = 0;}
    if (is_null($this->nPending) or ($n != $this->nPending)) {
      array_push($content, '"nPend":' . $n);
      $this->nPending = $n;
    }

    $this->tPrev = $now;

    if (!empty($content)) {
      echo "data: {" . implode(",", $content) . "}\n\n";
      ob_flush();
      flush();
    }
  }
}

$query = new Query($cmdDB);

while (True) {
  $query->sendIt();
  sleep(1);
}
?>
