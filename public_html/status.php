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
	private PDO $db;
	private PDOStatement $getController;
	private PDOStatement $getPOC;
	private PDOStatement $getSimulation;
	private PDOStatement $getCurrent;
	private PDOStatement $getFlow;
	private PDOStatement $getNumberOn;
	private PDOStatement $getPending;

	function __construct(string $dbName) {
		$db = new PDO("pgsql:dbname=$dbName;");
		$this->db = $db;
		$this->getController = $db->prepare("SELECT id,name FROM controller;");
		$this->getPOC = $db->prepare("SELECT sensor,name FROM pocFlow;");
		$this->getSimulation = $db->prepare("SELECT qSimulate FROM simulate;");
		$this->getCurrent = $db->prepare("SELECT controller AS ctl,volts,mAmps,"
			. "EXTRACT(EPOCH FROM timestamp) as tCurrent"
			. " FROM currentLog ORDER BY timestamp DESC LIMIT 1;");
		$this->getFlow = $db->prepare("SELECT pocFlow AS poc,flow,"
			. "EXTRACT(EPOCH FROM timestamp) as tFlow"
			. " FROM sensorLog ORDER BY timestamp DESC LIMIT 1;");
		$this->getNumberOn = $db->prepare("SELECT count(DISTINCT sensor) as nOn"
		       . " FROM action WHERE cmdOn IS NULL;");
		$this->getPending = $db->prepare("SELECT count(DISTINCT sensor) as nPending"
			. " FROM action"
			. " WHERE cmdOn IS NOT NULL"
			. " AND tOn<=(CURRENT_TIMESTAMP+INTERVAL '1 hour');");
		$db->exec("LISTEN currentlog_update;");
		$db->exec("LISTEN sensorlog_update;");
		$db->exec("LISTEN action_update;");
	}

	function notifications(int $dt) {
		$a = $this->db->pgsqlGetNotify(PDO::FETCH_ASSOC, $dt);
		if (!$a) return array();
		return ['channel' => $a['message'], 'payload' => $a['payload']];
	}

	function fetchData() {
		return array_merge(
			$this->fetchCurrent(),
			$this->fetchFlow(),
			$this->fetchNumberOn(),
			$this->fetchPending()
		);
	} // fetchData

	function fetchInitial() {
		$this->errors = [];
		$a = $this->fetchData();
		$a['controllers'] = $this->fetchControllers();
		$a['pocs'] = $this->fetchPOCs();
		$a['simulation'] = $this->fetchSimulation();
		$b = $this->fetchSystemctl();
		if (!empty($b)) $a['system'] = $b;

		if (!empty($this->errors)) {
			$a['errors'] = $this->errors;
			$this->errors = array();
		}
		return json_encode($a);
	} // fetchInitial

	function exec($stmt) {
		if ($stmt->execute([]) === false) {
			array_push($this->errors, $stmt->errorInfo());
			return false;
		}
		return true;
	} // exec

	function fetchControllers() {
		$stmt = $this->getController;
		if (!$this->exec($stmt)) return array();
		$a = array();
		while ($row = $stmt->fetch(PDO::FETCH_NUM)) $a[$row[0]] = $row[1];
		return $a;
	} // fetchControllers

	function fetchPOCs() {
		$stmt = $this->getPOC;
		if (!$this->exec($stmt)) return array();
		$a = array();
		while ($row = $stmt->fetch(PDO::FETCH_NUM)) $a[$row[0]] = $row[1];
		return $a;
	} // fetchPOCs

	function fetchSimulation() {
		$stmt = $this->getSimulation;
		if (!$this->exec($stmt)) return array();
		$info = array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			return $row['qsimulate'];
		}
		return $info;
	} // fetchSimulation

	function fetchCurrent() {
		$stmt = $this->getCurrent;
		if (!$this->exec($stmt)) return array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$row['volts'] = round($row['volts'] * 0.1, 1);
			$row['tcurrent'] = round($row['tcurrent']);
			return $row;
		}
		return array();
	} // fetchCurrent

	function fetchFlow() {
		$stmt = $this->getFlow;
		if (!$this->exec($stmt)) return array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$row['flow'] = round($row['flow'], 1);
			$row['tflow'] = round($row['tflow']);
			return $row;
		}
		return array();
	} // fetchFlow

	function fetchNumberOn() {
		$stmt = $this->getNumberOn;
		if (!$this->exec($stmt)) return array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) return $row;
		return array();
	} // fetchNumberOn

	function fetchPending() {
		$stmt = $this->getPending;
		if (!$this->exec($stmt)) return array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) return $row;
		return array();
	} // fetchPending

	function fetchSystemctl() {
		$output = shell_exec("/bin/systemctl is-active OITDI OISched OIAgriMet");
		if (empty($output)) return array();
		$output = explode("\n", $output);
		if (count($output) < 3) return array();
		return array_slice($output, 0, 3);
	}
} // DB

$delay = 55 * 1000; // 55 seconds between burps
$dbName = 'irrigation';

$db = new DB($dbName);

echo "data: " . $db->fetchInitial() . "\n\n";
$tPrev = time();

while (True) { # Wait forever
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	$info = array_merge(
		$db->notifications($delay),
		$db->fetchData()
	);
	if (($tPrev + 120) <= time()) { // Send system status
		$b = $db->fetchSystemctl();
		if (!empty($b)) $info['system'] = $b;
		$tPrev = time();
	}
	echo "data: " . json_encode($info) . "\n\n";
}
?>
