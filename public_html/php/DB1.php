<?php
class DB {
	private $db = null;
	private $lastError = null;
	private string $dbName;

	function __construct(string $dbName) {
		$this->dbName = $dbName;
	}

	private function getDB() {
		if ($this->db === null) {
			$this->db = new PDO("pgsql:dbname=" . $this->dbName . ";");
		}
		return $this->db;
	}

	function getError() {
		return $this->lastError === null ? "" : $this->lastError[2];
	}

	function close() { $this->db = null; }

	function prepare(string $sql) {
		$db = $this->getDB();
		$a = $db->prepare($sql);
		if ($a !== false) return $a;
		$this->lastError = $db->errorInfo();
		return false;
	}

	function query(string $sql, array $args = []) {
		$a = $this->prepare($sql);
		if ($a === false) return false;
		if ($a->execute($args) !== false) return $a; // worked
		$this->lastError = $a->errorInfo();
		return false;
	}

	function beginTransaction() : bool {return $this->db->beginTransaction();}
	function commit() : bool {return $this->db->commit();}
	function rollback() : bool {return $this->db->rollback();}

	function loadRows(string $sql, array $args) {
		$a = $this->query($sql, $args);
		if ($a === false) return [];
		return $a->fetchAll(PDO::FETCH_ASSOC);
	}

	function loadRowsNum(string $sql, array $args) {
		$a = $this->query($sql, $args);
		if ($a === false) return [];
		return $a->fetchAll(PDO::FETCH_NUM);
	}

	function quoteIdent(string $name): string {
		if (!preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*$/', $name)) {
			throw new InvalidArgumentException("Invalid SQL identifier: $name");
		}
		return $name;
	}

	function quote(string $value): string {
		return $this->getDB()->quote($value);
	}

	function listen(string $channel) {
		$channel = $this->quoteIdent($channel);
		return $this->query("LISTEN $channel;");
	}

	function notifications(int $delay) {
		$db = $this->getDB();
		return $db->pgsqlGetNotify(PDO::FETCH_ASSOC, $delay);
	}

	function tableExists(string $tbl) {
		$sql = "SELECT count(*) AS cnt FROM information_schema.tables"
			. " WHERE table_name=LOWER(?);";
		$a = $this->query($sql, [$tbl]);
		if ($a === false) return false;
		$result = $a->fetch(PDO::FETCH_ASSOC); // Should only be one row
		return array_key_exists('cnt', $result) && $result['cnt'];
	}

	function tableColumns(string $tbl) {
		$sql = "SELECT column_name AS col FROM information_schema.columns"
			. " WHERE table_name=LOWER(?);";
		$a = $this->query($sql, [$tbl]);
		if ($a === false) return [];
		$rows = [];
		foreach ($a as $row) { $rows[] = $row['col']; }
		return $rows;
	}

	function chgLog(string $addr, string $msg) {
		$sql = "INSERT INTO changeLog (ipAddr,description) VALUES(?,?);";
		$stmt = $this->prepare($sql);
		$stmt->execute([$addr, $msg]);
	}

	function mkMsg(bool $flag, string $msg) {
		$addr = array_key_exists("REMOTE_ADDR", $_SERVER) ? 
			$_SERVER["REMOTE_ADDR"] : "GotMe";
		$fn = array_key_exists("SCRIPT_NAME", $_SERVER) ? 
			basename($_SERVER["SCRIPT_NAME"]) : "GotMe";
		$sql = "INSERT INTO changeLog (ipAddr,description) VALUES(?,?);";
		$stmt = $this->prepare($sql);
		$stmt->execute([$addr, "$msg, $fn"]);
		return json_encode(["success" => $flag, "message" => $msg]);
	}

	function dbMsg(string $msg) {
		return $this->mkMsg(false, $msg . ", " . $this->getError());
	}
} // DB

$dbName = 'irrigation'; // Database name
$db = new DB($dbName);
