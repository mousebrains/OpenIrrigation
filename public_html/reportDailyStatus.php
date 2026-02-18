<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

// Send to JSON formatted data representing
// the previous 10 days and next 10 days
// daily run times

class DB {
	private $errors = array(); // Error stack
	private $daysBack = 9; # Days from current date to look backwards
	private $daysFwd =  9; # Days from current date to look forwards
	private PDO $db;
	private PDOStatement $getPast;
	private PDOStatement $getPending;
	private PDOStatement $getActive;
	private PDOStatement $getDates;
	private PDOStatement $getPgmStn;
	private PDOStatement $getStations;

	function __construct(string $dbName) {
		$db = new PDO("pgsql:dbname=$dbName;");
		$this->db = $db;

		$this->getPast = $db->prepare("SELECT "
			. "sensor,"
			. "tOn::DATE AS date,"
			. "ROUND(EXTRACT(EPOCH FROM SUM(tOff-tOn))) AS dt"
			. " FROM historical"
			. " WHERE tOn>=(CURRENT_DATE - INTERVAL '" . $this->daysBack . " days')"
			. " GROUP BY sensor,date;");

		$this->getPending = $db->prepare("SELECT "
			. "sensor,"
			. "tOn::DATE AS date,"
			. "ROUND(EXTRACT(EPOCH FROM SUM(tOff-tOn))) AS dt"
			. " FROM action"
			. " WHERE tOn<=(CURRENT_DATE + INTERVAL '" . ($this->daysFwd+1) . " days')"
			. " AND (cmdOn IS NOT NULL)"
			. " GROUP BY sensor,date;");

		$this->getActive = $db->prepare("SELECT "
			. "sensor,"
			. "tOn::DATE AS date,"
			. "ROUND(EXTRACT(EPOCH FROM tOn)) AS tOn,"
			. "ROUND(EXTRACT(EPOCH FROM tOff)) AS tOff"
			. " FROM action WHERE (cmdOn IS NULL);");

		$this->getDates = $db->prepare("SELECT "
			. "(CURRENT_DATE-INTERVAL '" . $this->daysBack . " days')::DATE"
			. "	AS earliest,"
			. "CURRENT_DATE AS today,"
			. "(CURRENT_DATE+INTERVAL '" . $this->daysFwd . " days')::DATE"
			. " AS latest;");

		$this->getPgmStn = $db->prepare("SELECT "
			. "station,program.label FROM pgmStn"
			. " INNER JOIN program ON program.id=pgmStn.program;");

		$this->getStations = $db->prepare("SELECT "
			. "id,sensor,name FROM station ORDER BY name;");

		$db->exec("LISTEN action_update;");
	} // __construct

	function notifications(int $dt) {
		$a = $this->db->pgsqlGetNotify(PDO::FETCH_ASSOC, $dt);
		if (!$a) return array();
		return ['channel' => $a['message'], 'payload' => $a['payload']];
	} // notifications

	function fetchInfo() { # Get all the pending and active actions
		$this->errors = [];
		$a = $this->getDates();
		$a['active'] = $this->loadInfo($this->getActive);
		$a['pending'] = $this->loadInfo($this->getPending);
		$a['past'] = $this->loadInfo($this->getPast);
		return $a;
	} // fetchInfo

	function fetchInitial() {
		$a = $this->fetchInfo();
		$a['info'] = $this->fetchStations();
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

	function loadInfo($stmt) { # Read all the rows from a result and return an array
		if (!$this->exec($stmt)) return array();
		return $stmt->fetchAll(PDO::FETCH_NUM);
	} // loadInfo

	function getDates() { # Get start/end date range
		$stmt = $this->getDates;
		if (!$this->exec($stmt)) return array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) return $row;
		return array(); // This should never be reached
	} // getDates

	function fetchStations() { # Get sensor/name and program/label 
		$stmt = $this->getPgmStn;
		if (!$this->exec($stmt)) return array();
		$s2p = array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$stn = $row['station'];
			if (!array_key_exists($stn, $s2p)) {
				$s2p[$stn] = array();
			}
			array_push($s2p[$stn], $row['label']);
		}

		$stmt = $this->getStations;
		if (!$this->exec($stmt)) return array();
		$a = array();
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$id = $row['id'];
			$b = [$row['sensor'], $row['name'],
				array_key_exists($id, $s2p) ? implode(', ', $s2p[$id]) : ''];
			array_push($a, $b);
		}

		return $a;
	}
} // DB

$delay = 55 * 1000; // 55 seconds between burps
$dbName = 'irrigation';

$db = new DB($dbName);

echo "data: " . $db->fetchInitial() . "\n\n";

while (!connection_aborted()) { # Wait until client disconnects
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
