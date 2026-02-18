<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

// Send process state records in JSON format

class DB {
	private $errors = []; // Error stack
	private PDO $db;
	private PDOStatement $getRecords;

	function __construct(string $dbName) {
		$db = new PDO("pgsql:dbname=$dbName;");
		$this->db = $db;

		$this->getRecords = $db->prepare(
			"SELECT DISTINCT ON (name) name,EXTRACT(EPOCH FROM timestamp),status"
			. " FROM processState WHERE timestamp>=to_timestamp(?)"
			. " ORDER BY name,timestamp DESC;");

		$db->exec("LISTEN processstate_update;");
	}

	function notifications(int $dt) {
		$a = $this->db->pgsqlGetNotify(PDO::FETCH_ASSOC, $dt);
		if (!$a) return [];
		return ['channel' => $a['message'], 'payload' => $a['payload']];
	} // notifications

	function fetchInfo(float $t) { # Get the most current records for each process
		$stmt = $this->getRecords;
		if ($stmt->execute([$t]) === false) return ['error' => $stmt->errorInfo()];
		return $stmt->fetchAll(PDO::FETCH_NUM);
	}
} // DB

$delay = 55 * 1000; // 55 seconds between burps
$dbName = 'irrigation';

$db = new DB($dbName);

$tPrev = time();
echo "data: " . json_encode($db->fetchInfo(0)) . "\n\n";

while (!connection_aborted()) { # Wait until client disconnects
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	$notifications = $db->notifications($delay);
	if (empty($notifications)) {
		$info = ['burp'=>0];
	} else {
		$now = time();
		$info = $db->fetchInfo($tPrev);
		$tPrev = $now;
	}
	echo "data: " . json_encode($info) . "\n\n";
}
