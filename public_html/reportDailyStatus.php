<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

// Send to JSON formatted data representing
// the previous 10 days and next 10 days
// daily run times

class Monitor { # Container to hold information for use by index.js
	function __construct($dbName) { # constructor
		$this->daysBack = 9; # Days from current date to look backwards
		$this->daysFwd = 9; # Days from current date to look forwards

		try {
			$this->db = pg_connect("dbname=$dbName");
		} catch (Exception $e) {
			throw($e);
		}

		$sql = "SELECT "
			. "sensor,"
			. "tOn::DATE AS date,"
			. "ROUND(EXTRACT(EPOCH FROM SUM(tOff-tOn))) AS dt"
			. " FROM historical"
			. " WHERE tOn>=(CURRENT_DATE - INTERVAL '" . $this->daysBack . " days')"
			. " GROUP BY sensor,date;";
		$result = pg_prepare($this->db, "get_past", $sql); # Get the historical info
		pg_free_result($result);

		$sql = "SELECT "
			. "sensor,"
			. "tOn::DATE AS date,"
			. "ROUND(EXTRACT(EPOCH FROM SUM(tOff-tOn))) AS dt"
			. " FROM action"
			. " WHERE tOn<=(CURRENT_DATE + INTERVAL '" . $this->daysFwd . " days')"
			. " AND (cmdOn IS NOT NULL)"
			. " GROUP BY sensor,date;";
		$result = pg_prepare($this->db, "get_pending", $sql); # Get the future info
		pg_free_result($result);

		$sql = "SELECT "
			. "sensor,"
			. "tOn::DATE AS date,"
			. "ROUND(EXTRACT(EPOCH FROM tOn)) AS tOn,"
			. "ROUND(EXTRACT(EPOCH FROM tOff)) AS tOff"
			. " FROM action WHERE (cmdOn IS NULL);";
		$result = pg_prepare($this->db, "get_active", $sql); # Get the active info
		pg_free_result($result);

		$sql = "SELECT"
			. " (CURRENT_DATE-INTERVAL '" . $this->daysBack . " days')::DATE"
			. "	AS earliest,"
			. " CURRENT_DATE AS today,"
			. " (CURRENT_DATE+INTERVAL '" . $this->daysFwd . " days')::DATE"
			. " AS latest;";
		$result = pg_prepare($this->db, "get_dates", $sql);
		pg_free_result($result);

		$result = pg_query($this->db, "LISTEN action_on_update;");
		pg_free_result($result);
	}

	function __destruct() { # Destructor
		if ($this->db != NULL) {
			pg_close($this->db);
		}
	}

	function getDates() { # Get start/end date range
		$result = pg_execute($this->db, "get_dates", []);
		while ($row = pg_fetch_assoc($result)) {
			return $row;
		}
		return array(); // This should never be reached
	}


	function fetchStations() { 
		# Get sensor/name and program/label 
		$sql = "SELECT station,program.label FROM pgmStn"
			. " INNER JOIN program ON program.id=pgmStn.program;";
		$result = pg_query($this->db, $sql);
		$s2p = array();
		while ($row = pg_fetch_assoc($result)) {
			$stn = $row['station'];
			if (!array_key_exists($stn, $s2p)) {
				$s2p[$stn] = array();
			}
			array_push($s2p[$stn], $row['label']);
		}
		pg_free_result($result);

		$sql = "SELECT id,sensor,name FROM station ORDER BY name;";
		$result = pg_query($this->db, $sql);
		$a = array();
		while ($row = pg_fetch_assoc($result)) { 
			$id = $row['id'];
			$b = [$row['sensor'], $row['name'],
				array_key_exists($id, $s2p) ? implode(', ', $s2p[$id]) : ''];
			array_push($a, $b);
		}
		pg_free_result($result);

		return $a;
	}

	function loadActive($result) { # Read all the rows from a result and return an array
		$a = [];
		while ($row = pg_fetch_assoc($result)) { // Walk through rows
			array_push($a, [$row['sensor'], $row['date'], 
				$row['ton'], $row['toff']]);
		}
		pg_free_result($result);
		return $a;
	}

	function loadInfo($result) { # Read all the rows from a result and return an array
		$a = [];
		while ($row = pg_fetch_assoc($result)) { // Walk through rows
			array_push($a, [$row['sensor'], $row['date'], $row['dt']]);
		}
		pg_free_result($result);
		return $a;
	}

	function fetchInfo() { # Get all the pending and active actions
		$a = $this->getDates();
		$a['active'] = $this->loadActive(pg_execute($this->db, "get_active", []));
		$a['pending'] = $this->loadInfo(pg_execute($this->db, "get_pending", []));
		$a['past'] = $this->loadInfo(pg_execute($this->db, "get_past", []));
		return $a;
	}

	function fetchInitial() {
		$a = $this->fetchInfo();
		$a['info'] = $this->fetchStations();
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
