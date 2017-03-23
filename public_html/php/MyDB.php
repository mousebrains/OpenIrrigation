<?php
class MyDB extends SQLite3 {
	function __construct(string $fn) {
		parent::__construct($fn, SQLITE3_OPEN_READWRITE);
                $this->busyTimeout(2000);
		$this->exec('PRAGMA foreign_keys=ON;');
        }

	function __destruct() {
                $this->close();
	}
}
?>
