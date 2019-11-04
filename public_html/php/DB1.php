<?php
class DB {
	private $db = null;
	private $lastError = null;

	function __construct(string $dbName) {
		$this->dbName = $dbName;
	}

	private function getDB() {
		if ($this->db == null) {
			$this->db = new PDO("pgsql:dbname=" . $this->dbName . ";");
		}
		return $this->db;
	}

	function getError() {
		return $this->lastError == null ? "" : $this->lastError[2];
	}

	function close() { $this->db = null; }

	function tableExists(string $tbl) {
		$sql = "SELECT count(*) AS cnt FROM information_schema.tables"
			. " WHERE table_name=LOWER(?);";
		$a = $this->query($sql, [$tbl]);
		if ($a == false) return $a;
		$result = $a->fetch(PDO::FETCH_ASSOC); // Should only be one row
		return array_key_exists('cnt', $result) && $result['cnt'];
	}

	function prepare(string $sql) {
		$db = $this->getDB();
		$a = $db->prepare($sql);
		if ($a != false) return $a;
		$lastError = $db->errorInfo();
		return false;
	}

	function query(string $sql, array $args) {
		$a = $this->prepare($sql);
		if ($a == false) return false;
		if ($a->execute($args) != false) return $a; // worked
		$this->lastError = $a->errorInfo();
		return false;
	}

	function loadRows(string $sql, array $args) {
		$a = $this->query($sql, $args);
		if ($a == false) return [];
		return $a->fetchAll(PDO::FETCH_ASSOC);
	}

	function listen(string $channel) {return $this->query("LISTEN $channel;", []);}

	function notifications(int $delay) {
		$db = $this->getDB();
		return $db->pgsqlGetNotify(PDO::FETCH_ASSOC, $delay);
	}

	function tableColumns(string $tbl) {
		$sql = "SELECT col FROM tableInfo WHERE tbl=?;";
		$a = $this->query($sql, [$tbl]);
		if ($a == false) return [];
		$rows = [];
		foreach ($a as $row) { array_push($rows, $row[0]); }
		return $rows;
	}
} // DB

$dbName = 'irrigation'; // Database name
$db = new DB($dbName);
?>
