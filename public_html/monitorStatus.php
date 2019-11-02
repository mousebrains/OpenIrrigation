<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

// Send to JSON formatted data representing
// the previous 10 days and next 10 days
// daily run times

class Monitor { # Container to hold information for use by index.js
	function __construct($dbName) { # constructor
		$this->daysFwd = 3; # Days from current date to look forwards
		$this->tPast = time() - 3 * 86400; # 3 days back

		try {
			$this->db = pg_connect("dbname=$dbName");
		} catch (Exception $e) {
			throw($e);
		}

		$sql = "SELECT "
			. "sensor,"
			. "program,"
			. "pre,peak,post,onCode,"
			. "ROUND(EXTRACT(EPOCH FROM tOn)) AS tOn,"
			. "ROUND(EXTRACT(EPOCH FROM tOff)) AS tOff"
			. " FROM action"
			. " WHERE cmdOn IS NULL"
			. " ORDER BY tOn,tOff;";
		$result = pg_prepare($this->db, "get_active", $sql); 
		pg_free_result($result);

		$sql = "SELECT "
			. "id,"
			. "sensor,"
			. "program,"
			. "ROUND(EXTRACT(EPOCH FROM tOn)) AS tOn,"
			. "ROUND(EXTRACT(EPOCH FROM tOff)) AS tOff"
			. " FROM action"
			. " WHERE tOn<=(CURRENT_TIMESTAMP + INTERVAL '" . $this->daysFwd . " days')"
			. " AND (cmdOn IS NOT NULL)"
		       	. " ORDER BY tOn,tOff;";
		$result = pg_prepare($this->db, "get_pending", $sql);
		pg_free_result($result);

		$sql = "SELECT "
			. "sensor,"
			. "program,"
			. "pre,peak,post,onCode,offCode,"
			. "EXTRACT(EPOCH FROM tOn) AS tOn,"
			. "EXTRACT(EPOCH FROM tOff) AS tOff"
			. " FROM historical"
			. ' WHERE tOff>to_timestamp($1)'
			. " ORDER BY tOff,tOn;";
		$result = pg_prepare($this->db, "get_historical", $sql); 
		pg_free_result($result);

		$result = pg_query($this->db, "LISTEN action_on_update;");
		pg_free_result($result);
	}

	function __destruct() { # Destructor
		if ($this->db != NULL) {
			pg_close($this->db);
		}
	}

	function fetchStations() { # Get sensor/name and program/label 
		$a = array();
		$sql = "SELECT sensor.id,sensor.name,station.name AS stn FROM sensor"
			. " LEFT JOIN station ON station.sensor=sensor.id;";
		$result = pg_query($this->db, $sql);
		while ($row = pg_fetch_assoc($result)) {
			$a[$row['id']] = $row['stn'] == '' ? $row['name'] : $row['stn'];
		}
		pg_free_result($result);
		return $a;
	}

	function fetchPrograms() {
		$a = array();
		$sql = "SELECT id,name FROM program;";
		$result = pg_query($this->db, $sql);
		while ($row = pg_fetch_assoc($result)) { 
			$a[$row['id']] = $row['name'];
		}
		pg_free_result($result);
		return $a;
	}

	function fetchPOCs() {
		$a = array();
		$sql = "SELECT poc.id,poc.name FROM poc INNER JOIN pocMV ON pocMV.poc=poc.id ORDER BY poc.name;";
		$result = pg_query($this->db, $sql);
		while ($row = pg_fetch_assoc($result)) { 
			$a[$row['id']] = $row['name'];
		}
		pg_free_result($result);
		return $a;
	}

	function loadInfo($result, $toSave) {
		$a = array();
		while ($row = pg_fetch_assoc($result)) { // Walk through rows
			$b = array();
			foreach($toSave as $key) {array_push($b, $row[$key]);}
			array_push($a, $b);
		}
		pg_free_result($result);
		return $a;
	}

	function fetchInfo() { # Get all the historical, pending, and active actions
		$a = array();
		$a['active'] = $this->loadInfo(pg_execute($this->db, "get_active", []),
			['sensor', 'program', 'pre', 'peak', 'post', 'oncode', 'ton', 'toff']);
		$a['pending'] = $this->loadInfo(pg_execute($this->db, "get_pending", []),
			['id', 'sensor', 'program', 'ton', 'toff']);
		$a['past'] = $this->loadInfo(pg_execute($this->db, "get_historical", [$this->tPast]),
			['sensor', 'program', 'pre', 'peak', 'post', 'oncode', 'offcode', 'ton', 'toff']);

		foreach($a['past'] as $item) {$this->tPast = max($this->tPast, $item[9]);}
		return $a;
	}

	function fetchInitial() {
		$a = $this->fetchInfo();
		$a['stations'] = $this->fetchStations();
		$a['programs'] = $this->fetchPrograms();
		$a['pocs'] = $this->fetchPOCs();
		return $a;
	}

	function notifications() {
		return pg_get_notify($this->db);
	}
}

$a = new Monitor("irrigation");

echo "data: " . json_encode($a->fetchInitial()) . "\n\n";
$tPrev = time(); // Current time

while (True) { # Wait forever
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	$notify = $a->notifications();
	if (!$notify) {
		$now = time(); // Current time
		if ($now >= ($tPrev + 50)) { // Avoid 1 minute timeout by burping
			echo "data: " . json_encode(['burp' => 0]) . "\n\n";
			$tPrev = $now;
		} else {
			sleep(5); # Wait a 5 seconds before checking on notifications again
		}
	} else {
		echo "data: " . json_encode($a->fetchInfo()) . "\n\n";
		$tPrev = time();
	}
}
?>
