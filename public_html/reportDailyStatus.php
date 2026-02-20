<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');
echo "retry: 10000\n\n";

// Send to JSON formatted data representing
// the previous 10 days and next 10 days
// daily run times

class ReportDB {
	/** @var array<mixed> */
	private array $errors = [];
	private int $daysBack = 9; // Days from current date to look backwards
	private int $daysFwd =  9; // Days from current date to look forwards
	private PDO $db;
	private PDOStatement $getPast;
	private PDOStatement $getPending;
	private PDOStatement $getActive;
	private PDOStatement $getDates;
	private PDOStatement $getPgmStn;
	private PDOStatement $getStations;
	private PDOStatement $getPastTargets;
	private PDOStatement $getPendingTargets;

	public function __construct(string $dbName) {
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

		$this->getPastTargets = $db->prepare("SELECT "
			. "sub.sensor,sub.date,ROUND(SUM(sub.runTime*60)) AS target"
			. " FROM ("
			. "SELECT DISTINCT h.sensor,h.tOn::DATE AS date,ps.id,ps.runTime"
			. " FROM historical h"
			. " INNER JOIN pgmStn ps ON ps.id=h.pgmStn"
			. " WHERE h.tOn>=(CURRENT_DATE - INTERVAL '" . $this->daysBack . " days')"
			. ") sub"
			. " GROUP BY sub.sensor,sub.date;");

		$this->getPendingTargets = $db->prepare("SELECT "
			. "sub.sensor,sub.date,ROUND(SUM(sub.runTime*60)) AS target"
			. " FROM ("
			. "SELECT DISTINCT a.sensor,a.tOn::DATE AS date,ps.id,ps.runTime"
			. " FROM action a"
			. " INNER JOIN pgmStn ps ON ps.id=a.pgmStn"
			. ") sub"
			. " GROUP BY sub.sensor,sub.date;");

		$db->exec("LISTEN action_update;");
	} // __construct

	/** @return array<string, mixed> */
	public function notifications(int $dt): array {
		$a = $this->db->pgsqlGetNotify(PDO::FETCH_ASSOC, $dt);
		if (!$a) return [];
		return ['channel' => $a['message'], 'payload' => $a['payload']];
	} // notifications

	/** @return array<string, mixed> */
	public function fetchInfo(): array { // Get all the pending and active actions
		$this->errors = [];
		$a = $this->getDates();
		$a['active'] = $this->loadInfo($this->getActive);
		$a['pending'] = $this->loadInfo($this->getPending);
		$a['past'] = $this->loadInfo($this->getPast);
		$a['pastTargets'] = $this->loadInfo($this->getPastTargets);
		$a['pendingTargets'] = $this->loadInfo($this->getPendingTargets);
		return $a;
	} // fetchInfo

	public function fetchInitial(): string {
		$a = $this->fetchInfo();
		$a['info'] = $this->fetchStations();
		if (!empty($this->errors)) {
			$a['errors'] = $this->errors;
			$this->errors = [];
		}
		return json_encode($a, JSON_THROW_ON_ERROR);
	} // fetchInitial
	
	private function exec(PDOStatement $stmt): bool {
		if ($stmt->execute([]) === false) {
			$this->errors[] = $stmt->errorInfo();
			return false;
		}
		return true;
	} // exec

	/** @return array<int, array<int, mixed>> */
	private function loadInfo(PDOStatement $stmt): array { // Read all the rows from a result and return an array
		if (!$this->exec($stmt)) return [];
		return $stmt->fetchAll(PDO::FETCH_NUM);
	} // loadInfo

	/** @return array<string, mixed> */
	private function getDates(): array { // Get start/end date range
		$stmt = $this->getDates;
		if (!$this->exec($stmt)) return [];
		$row = $stmt->fetch(PDO::FETCH_ASSOC);
		return $row !== false ? $row : [];
	} // getDates

	/** @return array<int, array<int|string, mixed>> */
	private function fetchStations(): array { // Get sensor/name and program/label
		$stmt = $this->getPgmStn;
		if (!$this->exec($stmt)) return [];
		$s2p = [];
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$stn = $row['station'];
			if (!isset($s2p[$stn])) {
				$s2p[$stn] = [];
			}
			$s2p[$stn][] = $row['label'];
		}

		$stmt = $this->getStations;
		if (!$this->exec($stmt)) return [];
		$a = [];
		while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
			$id = $row['id'];
			$b = [$row['sensor'], $row['name'],
				isset($s2p[$id]) ? implode(', ', $s2p[$id]) : ''];
			$a[] = $b;
		}

		return $a;
	}
} // DB

$delay = 55 * 1000; // 55 seconds between burps
require_once 'php/config.php';
$dbName = OI_DBNAME;

try {
	$db = new ReportDB($dbName);
} catch (\PDOException $e) {
	echo "data: " . json_encode(["error" => "Database connection failed"]) . "\n\n";
	exit;
}

echo "data: " . $db->fetchInitial() . "\n\n";

while (!connection_aborted()) { // Wait until client disconnects
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	try {
		$notifications = $db->notifications($delay);
		if (empty($notifications)) {
			echo "data: " . json_encode(['burp' => 0]) . "\n\n";
		} else {
			echo "data: " . json_encode($db->fetchInfo()) . "\n\n";
		}
	} catch (\Exception $e) {
		echo "data: " . json_encode(["error" => "Database error"]) . "\n\n";
	}
}
