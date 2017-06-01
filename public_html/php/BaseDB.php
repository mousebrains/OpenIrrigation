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
}
?>
