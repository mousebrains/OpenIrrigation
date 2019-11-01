<?php
// form submission from index.php

class Process { // process the form published from index.php
	public $info = array();

	function __construct(string $dbName) { # Constructor
		$this->dbName = $dbName;
		$this->info['success'] = true;
	}

	public function failure(string $msg) {
		$this->info['success'] = false;
		$this->info['message'] = $msg;
		return false;
	}

	public function turnOff(string $id, string $cmd) { # Turn a valve off 
		$name = $this->dbName;
		$db = pg_connect("dbname=$name");
		$sql = 'SELECT ' . $cmd . '($1)';
		if (pg_query_params($db, $sql, [$id])) {
			$this->info['message'] = "Turned off $id";
		} else {
			$this->failure(pg_last_error($db));
		}
		pg_close($db);
	}

	public function turnOn(string $id, string $dt, string $cmd) { 
		# Turn a valve on for dt minutes
		if (empty($dt)) {return $this->failure('dt was empty');}
		if ($dt <= 0) {return $this->failure("dt($dt)<=0");}
		$name = $this->dbName;
		$db = pg_connect("dbname=$name");
		$sql = 'SELECT ' . $cmd . '($1, $2)';
		if (pg_query_params($db, $sql, [$id, $dt])) {
			$this->info['message'] = "Turned on $id for $dt minutes";
		} else {
			$this->failure(pg_last_error($db));
		}
		pg_close($db);
	}
}

$a = new Process("irrigation");
if (empty($_POST['id'])) {
	$a->failure('No ID supplied.');
} else if (array_key_exists('poc', $_POST)) { // work on a POC
	if (array_key_exists('time', $_POST)) { // Turn a master valve on
		$a->turnOn($_POST['poc'], $_POST['time'], 'poc_off');
	} else { // Turn a master valve off
		$a->turnOn($_POST['poc'], 'poc_on');
	}
} else if (array_key_exists('time', $_POST)) { // Turn a valve on
	$a->turnOn($_POST['id'], $_POST['time'], 'manual_on');
} else { // Turn a valve off
	$a->turnOff($_POST['id'], 'manual_off');
}

echo json_encode($a->info);
?>
