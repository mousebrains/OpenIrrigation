<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

// Send to JSON formatted data representing
//   the controller's current,
//   the flow sensor's flow,
//   the number of stations turned on, and
//   the number of stations pending within the next 50-60 minutes

class DB {
	private $errors = array(); // Error stack
	private $daysFwd = 3; # Days from current date to look forwards
	private $tPast = 0;

	function __construct(string $dbName) {
		$this->tPast = time() - 3 * 86400; # 3 days back
		$db = new PDO("pgsql:dbname=$dbName;");
		$this->db = $db;

		$this->getActive = $db->prepare("SELECT "
			. "sensor,"
			. "program,"
			. "pre,peak,post,onCode,"
			. "ROUND(EXTRACT(EPOCH FROM tOn)) AS tOn,"
			. "ROUND(EXTRACT(EPOCH FROM tOff)) AS tOff"
			. " FROM action"
			. " WHERE cmdOn IS NULL"
			. " ORDER BY tOn,tOff;");

		$this->getPending = $db->prepare("SELECT "
			. "id,"
			. "sensor,"
			. "program,"
			. "ROUND(EXTRACT(EPOCH FROM tOn)) AS tOn,"
			. "ROUND(EXTRACT(EPOCH FROM tOff)) AS tOff"
			. " FROM action"
			. " WHERE tOn<=(CURRENT_TIMESTAMP + INTERVAL '" . $this->daysFwd . " days')"
			. " AND (cmdOn IS NOT NULL)"
		       	. " ORDER BY tOn,tOff;");

		$this->getPast = $db->prepare("SELECT "
			. "sensor,"
			. "program,"
			. "pre,peak,post,onCode,offCode,"
			. "EXTRACT(EPOCH FROM tOn) AS tOn,"
			. "EXTRACT(EPOCH FROM tOff) AS tOff"
			. " FROM historical"
			. ' WHERE tOff>to_timestamp(?)'
			. " ORDER BY tOff,tOn;");

		$this->getStations = $db->prepare("SELECT "
			. "sensor.id,sensor.name,station.name AS stn FROM sensor"
			. " LEFT JOIN station ON station.sensor=sensor.id;");

		$this->getPrograms = $db->prepare("SELECT id,name FROM program;");

		$this->getPOCs = $db->prepare("SELECT "
			. "poc.id,poc.name FROM poc INNER JOIN pocMV ON pocMV.poc=poc.id"
			. " ORDER BY poc.name;");

		$db->exec("LISTEN action_update;");
	}

	function notifications(int $dt) {
		$a = $this->db->pgsqlGetNotify(PDO::FETCH_ASSOC, $dt);
		if (!$a) return array();
		return ['channel' => $a['message'], 'payload' => $a['payload']];
	}

	function fetchInfo() { # Get all the historical, pending, and active actions
		$this->errors = [];
		$a = array();
		$a['active'] = $this->loadInfo($this->getActive, [],
			['sensor', 'program', 'pre', 'peak', 'post', 'oncode', 'ton', 'toff']);
		$a['pending'] = $this->loadInfo($this->getPending, [],
			['id', 'sensor', 'program', 'ton', 'toff']);
		$a['past'] = $this->loadInfo($this->getPast, [$this->tPast],
			['sensor', 'program', 'pre', 'peak', 'post', 'oncode', 'offcode', 
			'ton', 'toff']);

		foreach($a['past'] as $item) {$this->tPast = max($this->tPast, $item[8]);}
		return $a;
	}

	function fetchInitial() {
		$a = $this->fetchInfo();
		$a['stations'] = $this->fetchStations();
		$a['programs'] = $this->fetchPrograms();
		$a['pocs'] = $this->fetchPOCs();
		if (!empty($this->errors)) {
			$a['errors'] = $this->errors;
			$this->errors = array();
		}
		return json_encode($a);
	}

	function exec($stmt, $args = []) {
		if ($stmt->execute($args) == false) {
			array_push($this->errors, $stmt->errorInfo());
			return false;
		}
		return true;
	} // exec

	function loadInfo($stmt, $args, $toSave) {
		if (!$this->exec($stmt, $args)) return array();
		$a = array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) { // Walk through rows
			$b = array();
			foreach($toSave as $key) {array_push($b, $row[$key]);}
			array_push($a, $b);
		}
		return $a;
	}

	function fetchStations() { # Get sensor/name and program/label 
		$stmt = $this->getStations;
		if (!$this->exec($stmt)) return array();
		$a = array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$a[$row['id']] = $row['stn'] == '' ? $row['name'] : $row['stn'];
		}
		return $a;
	}

	function fetchPrograms() {
		$stmt = $this->getPrograms;
		if (!$this->exec($stmt)) return array();
		$a = array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$a[$row['id']] = $row['name'];
		}
		return $a;
	}

	function fetchPOCs() {
		$stmt = $this->getPOCs;
		if (!$this->exec($stmt)) return array();
		$a = array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$a[$row['id']] = $row['name'];
		}
		return $a;
	}
} // DB

$delay = 55 * 1000; // 55 seconds between burps
$dbName = 'irrigation';

$db = new DB($dbName);

echo "data: " . $db->fetchInitial() . "\n\n";

while (True) { # Wait forever
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	$notifications = $db->notifications($delay);
	if (empty($notifications)) {
		echo "data: " . json_encode(['burp' => 0]) . "\n\n";
	} else {
		echo "data: " . json_encode($db->fetchInfo()) . "\n\n";
	}
}
?>
