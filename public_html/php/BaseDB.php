<?php
class BaseDB extends SQLite3 {
	function __construct(string $fn) {
		$this->filename = $fn;
		parent::__construct($fn, SQLITE3_OPEN_READWRITE);
                $this->busyTimeout(2000);
        }

	function __destruct() {
                $this->close();
	}

	function loadColumn(string $sql) {
		$rows = [];
		$results = $this->query($sql);
		while ($row = $results->fetchArray()) {array_push($rows, $row[0]);}
		return $rows;
	}

	function loadKeyValue(string $sql) {
		$rows = [];
		$results = $this->query($sql);
		while ($row = $results->fetchArray()) {$rows[$row[0]] = $row[1];}
		return $rows;
	}
}
?>
