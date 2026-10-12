<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');
echo "retry: 10000\n\n";

// Send process state records in JSON format

class ProcessDB {
	private PDO $db;
	private PDOStatement $getRecords;

	function __construct(string $dbName) {
		$db = new PDO("pgsql:dbname=$dbName;", null, null,
			[PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
		$this->db = $db;

		$this->getRecords = $db->prepare(
			"SELECT DISTINCT ON (name) name,EXTRACT(EPOCH FROM timestamp),status"
			. " FROM processState WHERE timestamp>=to_timestamp(?)"
			. " ORDER BY name,timestamp DESC;");

		$db->exec("LISTEN processstate_update;");
	}

	/** @return array<string, mixed> */
	function notifications(int $dt): array {
		$a = DB::waitNotify($this->db, $dt);
		if (!$a) return [];
		return ['channel' => $a['message'], 'payload' => $a['payload']];
	} // notifications

	/** @return array<int|string, mixed> */
	function fetchInfo(float $t): array { # Get the most current records for each process
		$stmt = $this->getRecords;
		if ($stmt->execute([$t]) === false) return ['error' => $stmt->errorInfo()];
		return $stmt->fetchAll(PDO::FETCH_NUM);
	}
} // DB

$delay = 25 * 1000; // 25 seconds between burps; keeps iOS WiFi power-save from dropping idle connection
require_once 'php/DB1.php';
require_once 'php/config.php';
$dbName = OI_DBNAME;

try {
	$db = new ProcessDB($dbName);
	$tPrev = time();
	echo "data: " . json_encode($db->fetchInfo(0)) . "\n\n";
} catch (\PDOException $e) {
	echo "data: " . json_encode(["error" => "Database connection failed"]) . "\n\n";
	exit;
}

while (!connection_aborted()) { # Wait until client disconnects
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	try {
		$notifications = $db->notifications($delay);
		if (empty($notifications)) {
			$info = ['burp'=>0];
		} else {
			$now = time();
			$info = $db->fetchInfo($tPrev);
			$tPrev = $now;
		}
		echo "data: " . json_encode($info) . "\n\n";
	} catch (\Exception $e) {
		echo "data: " . json_encode(["error" => "Database error"]) . "\n\n";
		break; // Dead DB connection would busy-loop; let EventSource reconnect
	}
}
