<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

// Send to JSON formatted data representing
//  All the stations, and changes to their states.
//  For use by index.php and index.js

class Index { # Container to hold information for use by index.js
	function __construct($dbName) { # constructor
		try {
			$this->db = pg_connect("dbname=$dbName");
		} catch (Exception $e) {
			throw($e);
		}

		$this->hoursPast = 24; # How many hours into the past to look for events
		$this->hoursFuture = 24; # How many hours into the future to look for pending

		$sql = "SELECT sensor,"
			. "EXTRACT(EPOCH FROM tOn) AS tOn,"
			. "EXTRACT(EPOCH FROM tOff) AS tOFF"
			. " FROM action"
			. " WHERE cmdOn IS NULL"
			. " ORDER BY tOn,tOff;";
		$result = pg_prepare($this->db, "get_active", $sql); # Get all the active actions
		pg_free_result($result);

		$sql = "SELECT sensor,"
			. "EXTRACT(EPOCH FROM tOn) AS tOn,"
			. "EXTRACT(EPOCH FROM tOff) AS tOFF"
			. " FROM action"
			. " WHERE cmdOn IS NOT NULL"
			. " AND tOn <= (CURRENT_TIMESTAMP + INTERVAL '" 
			. $this->hoursFuture 
			. " hours')"
			. " ORDER BY tOn,tOff;";
		$result = pg_prepare($this->db, "get_pending", $sql); # Get all the pending actions
		pg_free_result($result);

		$sql = "SELECT sensor,"
			. "EXTRACT(EPOCH FROM tOn) AS tOn,"
			. "EXTRACT(EPOCH FROM tOff) AS tOFF"
			. " FROM historical"
			. " WHERE tOn >= (CURRENT_TIMESTAMP - INTERVAL '"
			. $this->hoursPast
			. " hours')"
			. " ORDER BY tOn DESC, tOff DESC;";
		$result = pg_prepare($this->db, "get_past", $sql); # Get all the recent actions
		pg_free_result($result);

		$result = pg_query($this->db, "LISTEN action_on_update;");
		pg_free_result($result);
	}

	function __destruct() { # Destructor
		if ($this->db != NULL) {
			pg_close($this->db);
		}
	}

	function fetchStations() { # Get sensor/name relationships for all stations
		// From station table
		$sql = "SELECT sensor,name FROM station ORDER BY name;";
		$result = pg_query($this->db, $sql);
		$a = array();
		while ($row = pg_fetch_assoc($result)) { 
			array_push($a, [$row['sensor'], $row['name']]);
		}
		pg_free_result($result);
		return $a;
	}
	
	function fetchPOCs() { 
		// Get the point-of-connect/name map for all POCs with master valves
		$sql = "SELECT "
			. "pocmv.sensor AS key,"
			. "pocmv.name AS name,"
			. "poc.name AS poc,"
			. "poc.id AS id"
			. " FROM pocmv"
			. " INNER JOIN poc ON poc.id=pocmv.poc"
			. " ORDER BY poc.name,pocmv.name;";
		$result = pg_query($this->db, $sql);
		$a = array();
		while ($row = pg_fetch_assoc($result)) {
			array_push($a, [$row['key'], $row['poc'] . '::' . $row['name'],
				$row['id']]);
		}
		pg_free_result($result);

		return $a;
	}

	function loadInfo($result) { # Read all the rows from a result and return an array
		$a = [];
		while ($row = pg_fetch_assoc($result)) { // Walk through rows
			$id = $row['sensor'];
			$tOn = $row['ton'];
			$tOff = $row['toff'];
			if (!array_key_exists($id, $a)) {$a[$id] = [];}
			array_push($a[$id], [$tOn, $tOff]);
		}
		pg_free_result($result);
		return $a;
	}

	function fetchInfo() { # Get all the pending and active actions
		$a = $this->loadInfo(pg_execute($this->db, "get_active", []));
		$b = $this->loadInfo(pg_execute($this->db, "get_pending", []));
		$c = $this->loadInfo(pg_execute($this->db, "get_past", []));
		return ["active"=>$a, "pending"=>$b, "past"=>$c];
	}

	function fetchInitial() {
		$a = $this->fetchInfo();
		$b = $this->fetchStations();
		if (!empty($b)) {$a['info'] = $b;}
		$c = $this->fetchPOCs();
		if (!empty($c)) {$a['pocs'] = $c;}
		$a['hoursPast'] = $this->hoursPast;
		$a['hoursFuture'] = $this->hoursFuture;
		return $a;
	}

	function notifications() {
		return pg_get_notify($this->db);
	}
}

$a = new Index("irrigation");

echo "data: " . json_encode($a->fetchInitial()) . "\n\n";
$tPrev = time(); // Current time
$tInfo = $tPrev; // Last time fetchInfo was sent

while (True) { # Wait forever
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	$notify = $a->notifications();
	if (!$notify) {
		$now = time(); // Current time
		if ($now >= ($tInfo + (15 * 60))) { // Refresh every n minutes
			echo "data: " . json_encode($a->fetchInfo()) . "\n\n";
			$tPrev = time();
			$tInfo = $tPrev;
		} else if ($now >= ($tPrev + 50)) { // Avoid 1 minute timeout by burping
			echo "data: " . json_encode(['burp' => 0]) . "\n\n";
			$tPrev = $now;
		} else {
			usleep(500000); # Wait a 0.5 seconds before checking on notifications again
		}
	} else {
		echo "data: " . json_encode($a->fetchInfo()) . "\n\n";
		$tPrev = time();
		$tInfo = $tPrev;
	}
}
?>
