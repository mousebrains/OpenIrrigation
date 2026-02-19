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
			try {
				$this->db = new PDO("pgsql:dbname=" . $this->dbName . ";");
			} catch (\PDOException $e) {
				$this->lastError = [0, $e->getCode(), $e->getMessage()];
				error_log("DB connection failed: " . $e->getMessage());
				return null;
			}
		}
		return $this->db;
	}

	function isConnected(): bool {
		return $this->getDB() !== null;
	}

	function getError() {
		return $this->lastError === null ? "" : $this->lastError[2];
	}

	function close() { $this->db = null; }

	function prepare(string $sql) {
		$db = $this->getDB();
		if ($db === null) return false;
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

	function beginTransaction() : bool {return $this->db ? $this->db->beginTransaction() : false;}
	function commit() : bool {return $this->db ? $this->db->commit() : false;}
	function rollback() : bool {return $this->db ? $this->db->rollback() : false;}

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
		$db = $this->getDB();
		if ($db === null) return "'" . addslashes($value) . "'";
		return $db->quote($value);
	}

	function listen(string $channel) {
		$channel = $this->quoteIdent($channel);
		return $this->query("LISTEN $channel;");
	}

	function notifications(int $delay) {
		$db = $this->getDB();
		if ($db === null) return false;
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
		if ($stmt === false || $stmt->execute([$addr, $msg]) === false) {
			error_log("chgLog failed: " . $this->getError());
		}
	}

	function mkMsg(bool $flag, string $msg) {
		$addr = array_key_exists("REMOTE_ADDR", $_SERVER) ? 
			$_SERVER["REMOTE_ADDR"] : "GotMe";
		$fn = array_key_exists("SCRIPT_NAME", $_SERVER) ? 
			basename($_SERVER["SCRIPT_NAME"]) : "GotMe";
		$sql = "INSERT INTO changeLog (ipAddr,description) VALUES(?,?);";
		$stmt = $this->prepare($sql);
		if ($stmt === false || $stmt->execute([$addr, "$msg, $fn"]) === false) {
			error_log("mkMsg chgLog failed: " . $this->getError());
		}
		return json_encode(["success" => $flag, "message" => $msg]);
	}

	function dbMsg(string $msg) {
		return $this->mkMsg(false, $msg . ", " . $this->getError());
	}

	static function isValidCriteria(string $s): bool {
		// Allow: identifier='literal' (all current refCriteria values)
		return preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*=\'[a-zA-Z0-9_]+\'$/', $s) === 1;
	}

	static function isValidOrderBy(string $s): bool {
		// Allow: comma-separated identifiers (all current refOrderBy values)
		foreach (explode(',', $s) as $part) {
			if (!preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*$/', trim($part))) return false;
		}
		return true;
	}

	private static ?DB $instance = null;

	static function getInstance(): DB {
		if (self::$instance === null) {
			require_once __DIR__ . '/config.php';
			self::$instance = new DB(OI_DBNAME);
		}
		return self::$instance;
	}
} // DB
