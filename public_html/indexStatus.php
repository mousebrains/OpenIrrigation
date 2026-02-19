<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');
echo "retry: 10000\n\n";

// Send to JSON formatted data representing
//  All the stations, and changes to their states.
//  For use by index.php and index.js

class IndexDB {
	private $errors = []; // Error stack
	private PDO $db;
	private int $hoursPast;
	private int $hoursFuture;
	private PDOStatement $getActive;
	private PDOStatement $getPending;
	private PDOStatement $getPast;
	private PDOStatement $getStations;
	private PDOStatement $getPOCs;

	function __construct(string $dbName) {
		try {
			$db = new PDO("pgsql:dbname=$dbName;");
		} catch (\PDOException $e) {
			throw $e;
		}
		$this->db = $db;
		$this->hoursPast = 24; # How many hours into the past to look for events
		$this->hoursFuture = 24; # How many hours into the future to look for pending

		$this->getActive = $db->prepare(
			"SELECT sensor,"
			. "EXTRACT(EPOCH FROM tOn) AS tOn,"
			. "EXTRACT(EPOCH FROM tOff) AS tOFF"
			. " FROM action"
			. " WHERE cmdOn IS NULL"
			. " ORDER BY tOn,tOff;");

		$this->getPending = $db->prepare(
		       	"SELECT sensor,"
			. "EXTRACT(EPOCH FROM tOn) AS tOn,"
			. "EXTRACT(EPOCH FROM tOff) AS tOFF"
			. " FROM action"
			. " WHERE cmdOn IS NOT NULL"
			. " AND tOn <= (CURRENT_TIMESTAMP + INTERVAL '" 
			. $this->hoursFuture 
			. " hours')"
			. " ORDER BY tOn,tOff;");

		$this->getPast = $db->prepare(
		       	"SELECT sensor,"
			. "EXTRACT(EPOCH FROM tOn) AS tOn,"
			. "EXTRACT(EPOCH FROM tOff) AS tOFF"
			. " FROM historical"
			. " WHERE tOn >= (CURRENT_TIMESTAMP - INTERVAL '"
			. $this->hoursPast
			. " hours')"
			. " ORDER BY tOn DESC, tOff DESC;");

		$this->getStations = $db->prepare(
			"SELECT sensor,name FROM station ORDER BY name;");

		$this->getPOCs = $db->prepare(
			"SELECT "
			. "pocmv.sensor AS key,"
			. "pocmv.name AS name,"
			. "poc.name AS poc,"
			. "poc.id AS id"
			. " FROM pocmv"
			. " INNER JOIN poc ON poc.id=pocmv.poc"
			. " ORDER BY poc.name,pocmv.name;");

		$db->exec("LISTEN action_update;");
	}

	function notifications(int $dt) {
		$a = $this->db->pgsqlGetNotify(PDO::FETCH_ASSOC, $dt);
		if (!$a) return [];
		return ['channel' => $a['message'], 'payload' => $a['payload']];
	} // notifications

	function fetchInfo() { # Get all the pending and active actions
		$this->errors = [];
		$a = $this->loadInfo($this->getActive);
		$b = $this->loadInfo($this->getPending);
		$c = $this->loadInfo($this->getPast);
		return ["active"=>$a, "pending"=>$b, "past"=>$c];
	} // fetchInfo

	function fetchInitial() {
		$a = $this->fetchInfo();
		$b = $this->fetchStations();
		if (!empty($b)) {$a['info'] = $b;}
		$c = $this->fetchPOCs();
		if (!empty($c)) {$a['pocs'] = $c;}
		$a['hoursPast'] = $this->hoursPast;
		$a['hoursFuture'] = $this->hoursFuture;
		if (!empty($this->errors)) {
			$a['errors'] = $this->errors;
			$this->errors = [];
		}
		return json_encode($a);
	} // fetchInitial

	function exec($stmt) {
		if ($stmt->execute([]) === false) {
			$this->errors[] = $stmt->errorInfo();
			return false;
		}
		return true;
	} // exec

	function loadInfo($stmt) { # Read all the rows from a result and return an array
		if (!$this->exec($stmt)) return [];
		$a = [];
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$id = $row['sensor'];
			$tOn = $row['ton'];
			$tOff = $row['toff'];
			if (!array_key_exists($id, $a)) {$a[$id] = [];}
			$a[$id][] = [$tOn, $tOff];
		}
		return $a;
	} // loadInfo

	function fetchStations() { # Get sensor/name relationships for all stations
		$stmt = $this->getStations;
		if (!$this->exec($stmt)) return [];
		return $stmt->fetchAll(PDO::FETCH_NUM);
	}
	
	function fetchPOCs() { 
		// Get the point-of-connect/name map for all POCs with master valves
		$stmt = $this->getPOCs;
		if (!$this->exec($stmt)) return [];
		$a = [];
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$a[] = [$row['key'], $row['poc'] . '::' . $row['name'],
				$row['id']];
		}
		return $a;
	}
} // DB

$delay = 55 * 1000; // 55 seconds between burps
require_once 'php/config.php';
$dbName = OI_DBNAME;

try {
	$db = new IndexDB($dbName);
} catch (\PDOException $e) {
	echo "data: " . json_encode(["error" => "Database connection failed"]) . "\n\n";
	exit;
}

echo "data: " . $db->fetchInitial() . "\n\n";

while (!connection_aborted()) { # Wait until client disconnects
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	try {
		$info = array_merge(
			$db->notifications($delay),
			$db->fetchInfo()
		);
		echo "data: " . json_encode($info) . "\n\n";
	} catch (\Exception $e) {
		echo "data: " . json_encode(["error" => "Database error"]) . "\n\n";
	}
}
