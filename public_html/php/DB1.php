<?php
class DB {
	private ?PDO $db = null;
	private string $dbName;

	function __construct(string $dbName) {
		$this->dbName = $dbName;
	}

	// Connect on first use. Errors are exceptions everywhere (PHP 8's default,
	// set explicitly so a failed statement can never pass for a success):
	// action endpoints catch PDOException and answer with errMsg().
	private function getDB(): PDO {
		if ($this->db === null) {
			$this->db = new PDO("pgsql:dbname=" . $this->dbName . ";", null, null,
				[PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
		}
		return $this->db;
	}

	function isConnected(): bool {
		try {
			$this->getDB();
			return true;
		} catch (PDOException $e) {
			error_log("DB connection failed: " . $e->getMessage());
			return false;
		}
	}

	function close(): void { $this->db = null; }

	function prepare(string $sql): PDOStatement {
		$stmt = $this->getDB()->prepare($sql);
		if ($stmt === false) throw new PDOException("Unable to prepare $sql");
		return $stmt;
	}

	/** @param array<mixed> $args */
	function query(string $sql, array $args = []): PDOStatement {
		$stmt = $this->prepare($sql);
		$stmt->execute($args);
		return $stmt;
	}

	function beginTransaction(): bool { return $this->getDB()->beginTransaction(); }
	function commit(): bool { return $this->getDB()->commit(); }

	// Safe to call from an error path: never throws
	function rollback(): void {
		try {
			if ($this->db !== null && $this->db->inTransaction()) $this->db->rollBack();
		} catch (PDOException $e) {
			error_log("rollback failed: " . $e->getMessage());
		}
	}

	/** @param array<mixed> $args
	 * @return array<int, array<string, mixed>> */
	function loadRows(string $sql, array $args): array {
		return $this->query($sql, $args)->fetchAll(PDO::FETCH_ASSOC);
	}

	/** @param array<mixed> $args
	 * @return array<int, array<int, mixed>> */
	function loadRowsNum(string $sql, array $args): array {
		return $this->query($sql, $args)->fetchAll(PDO::FETCH_NUM);
	}

	function quoteIdent(string $name): string {
		// \z, not $: $ also matches before a trailing newline
		if (!preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*\z/', $name)) {
			throw new InvalidArgumentException("Invalid SQL identifier: $name");
		}
		return $name;
	}

	function listen(string $channel): void {
		$channel = $this->quoteIdent($channel);
		$this->query("LISTEN $channel;");
	}

	/** @return array<mixed>|false */
	function notifications(int $delay): array|false {
		return self::waitNotify($this->getDB(), $delay);
	}

	// Wait up to $totalMs for a NOTIFY on $pdo. An SSE endpoint learns that
	// its client has gone only when a write fails (PHP then aborts the
	// script), so write an SSE comment line, which EventSource ignores, every
	// $probeMs: a closed tab frees its php-fpm worker within seconds instead
	// of holding it until the next 25-second burp.
	/** @return array<mixed>|false */
	static function waitNotify(PDO $pdo, int $totalMs, int $probeMs = 5000): array|false {
		for ($waited = 0; $waited < $totalMs; $waited += $probeMs) {
			$a = $pdo->pgsqlGetNotify(PDO::FETCH_ASSOC, min($probeMs, $totalMs - $waited));
			if ($a) return $a; // false when nothing arrived in time
			echo ": \n\n";
			if (ob_get_length()) {ob_flush();}
			flush();
			if (connection_aborted()) return false;
		}
		return false;
	}

	// The generic table endpoints may only touch the tables the editor is
	// configured for: those named in tableInfo (case-insensitively) that
	// exist in the public schema. Returns tableInfo's spelling, else null.
	function tableName(string $tbl): ?string {
		$sql = "SELECT i.tbl FROM tableInfo i"
			. " INNER JOIN information_schema.tables t"
			. " ON t.table_schema='public' AND t.table_name=LOWER(i.tbl)"
			. " WHERE LOWER(i.tbl)=LOWER(?) LIMIT 1;";
		$name = $this->query($sql, [$tbl])->fetchColumn();
		return is_string($name) ? $name : null;
	}

	// The columns of $tbl that tableInfo lets the editor show and change,
	// as column name => tableInfo.inputType. tableInfo rows that describe a
	// secondary table are not columns of $tbl and are left out.
	/** @return array<string, string> */
	function tableColumns(string $tbl): array {
		$sql = "SELECT c.column_name,i.inputType FROM tableInfo i"
			. " INNER JOIN information_schema.columns c"
			. " ON c.table_schema='public' AND c.table_name=LOWER(i.tbl)"
			. " AND c.column_name=LOWER(i.col)"
			. " WHERE i.tbl=? AND i.secondaryKey IS NULL"
			. " ORDER BY i.displayOrder;";
		$cols = [];
		foreach ($this->loadRowsNum($sql, [$tbl]) as $row) {
			$cols[(string) $row[0]] = (string) $row[1];
		}
		return $cols;
	}

	function hasColumn(string $tbl, string $col): bool {
		$sql = "SELECT 1 FROM information_schema.columns"
			. " WHERE table_schema='public' AND table_name=LOWER(?) AND column_name=LOWER(?);";
		return $this->query($sql, [$tbl, $col])->fetchColumn() !== false;
	}

	// Record a change in the audit trail, inside the caller's transaction
	// so the record commits or rolls back with the change. Throws on error.
	function audit(string $msg): void {
		$addr = $_SERVER["REMOTE_ADDR"] ?? "GotMe";
		$this->query("INSERT INTO changeLog (ipAddr,description) VALUES(?,?);",
			[is_string($addr) ? $addr : "GotMe", $msg]);
	}

	// Record a change that has already been made. A failure to log is
	// reported to the PHP error log but never fails the change.
	function chgLog(string $msg): void {
		try {
			$this->audit($msg);
		} catch (PDOException $e) {
			error_log("chgLog failed: " . $e->getMessage());
		}
	}

	// JSON reply for an action endpoint. Successes are changes, so they go
	// to changeLog; failures (bad input, refused or failed statements) went
	// nowhere near the data and go to the PHP error log instead, so neither
	// a GET nor a stream of bad requests writes the audit trail.
	function mkMsg(bool $flag, string $msg): string {
		$fn = basename(is_string($_SERVER["SCRIPT_NAME"] ?? null) ? $_SERVER["SCRIPT_NAME"] : "GotMe");
		if ($flag) {
			$this->chgLog("$msg, $fn");
		} else {
			error_log("$fn: " . json_encode($msg, JSON_INVALID_UTF8_SUBSTITUTE));
		}
		return json_encode(
			["success" => $flag, "message" => $msg],
			JSON_THROW_ON_ERROR | JSON_INVALID_UTF8_SUBSTITUTE
		);
	}

	// The first line of PostgreSQL's message ("ERROR:  ..." prefix dropped)
	// and its DETAIL line, if any.
	/** @return array{string, string} */
	static function pgMessage(PDOException $e): array {
		$info = $e->errorInfo;
		$text = is_array($info) && isset($info[2]) && is_string($info[2]) ? $info[2] : $e->getMessage();
		$lines = explode("\n", $text);
		$msg = trim((string) preg_replace('/^(ERROR|FATAL):\s+/', '', $lines[0]));
		$detail = '';
		foreach ($lines as $line) {
			if (str_starts_with($line, 'DETAIL:')) $detail = trim(substr($line, 7));
		}
		return [$msg, $detail];
	}

	// JSON failure reply for a PDOException raised while doing $what
	function errMsg(PDOException $e, string $what): string {
		$this->rollback();
		[$msg, $detail] = self::pgMessage($e);
		switch (is_array($e->errorInfo) ? $e->errorInfo[0] : null) {
			case '23505': // unique_violation
				$msg = "already exists" . ($detail === '' ? '' : " ($detail)");
				break;
			case '23503': // foreign_key_violation
				$msg = "refers to a missing row or is still in use"
					. ($detail === '' ? '' : " ($detail)");
				break;
		}
		return $this->mkMsg(false, "$what: $msg");
	}

	static function isValidCriteria(string $s): bool {
		// Allow: identifier='literal' (all current refCriteria values)
		return preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*=\'[a-zA-Z0-9_]+\'\z/', $s) === 1;
	}

	static function isValidOrderBy(string $s): bool {
		// Allow: comma-separated identifiers (all current refOrderBy values)
		foreach (explode(',', $s) as $part) {
			if (!preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*\z/', trim($part))) return false;
		}
		return true;
	}

	// The database name, from config.php, which make generates
	static function dbName(): string {
		require_once __DIR__ . '/config.php';
		return OI_DBNAME;
	}

	private static ?DB $instance = null;

	static function getInstance(): DB {
		if (self::$instance === null) {
			self::$instance = new DB(self::dbName());
		}
		return self::$instance;
	}
} // DB
