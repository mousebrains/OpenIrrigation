<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

// Send to JSON formatted data representing
//   the controller's current,
//   the flow sensor's flow,
//   the number of stations turned on, and
//   the number of stations pending within the next 50-60 minutes

class Status { # Container to hold information for getting status updates
	function __construct($dbName) { # constructor
		try {
			$this->db = pg_connect("dbname=$dbName");
		} catch (Exception $e) {
			throw($e);
		}
		$result = pg_prepare($this->db, # Get most recent item
			"get_current",
			"SELECT controller AS ctl,volts,mAmps,"
			. "EXTRACT(EPOCH FROM timestamp) as tCurrent"
			. " FROM currentLog ORDER BY timestamp DESC LIMIT 1;");
		pg_free_result($result);
		$result = pg_prepare($this->db, # Get most recent item
			"get_flow",
			"SELECT pocFlow AS poc,flow,"
			. "EXTRACT(EPOCH FROM timestamp) as tFlow"
		       	. " FROM sensorLog ORDER BY timestamp DESC LIMIT 1;");
		pg_free_result($result);
		$result = pg_prepare($this->db, # Get most recent item
			"get_nOn",
			"SELECT count(DISTINCT sensor) as nOn FROM action WHERE cmdOn IS NULL;");
		pg_free_result($result);
		$result = pg_prepare($this->db, # Get # pending within $1 time from now
			"get_nPending",
			"SELECT count(DISTINCT sensor) as nPending FROM action " .
			"WHERE cmdOn IS NOT NULL AND tOn<=(CURRENT_TIMESTAMP+INTERVAL '1 hour');");
		pg_free_result($result);
		$result = pg_query($this->db, "LISTEN currentlog_update;");
		pg_free_result($result);
		$result = pg_query($this->db, "LISTEN sensorlog_update;");
		pg_free_result($result);
		$result = pg_query($this->db, "LISTEN action_on_update;");
		pg_free_result($result);
	}

	function __destruct() { # Destructor
		if ($this->db != NULL) {
			pg_close($this->db);
		}
	}

	function fetchControllers() { # Get controller ids to names
		$a = [];
		$result = pg_query($this->db, "SELECT id,name FROM controller;");
		while ($row = pg_fetch_assoc($result)) {
			$a[$row['id']] = $row['name'];
		}
		pg_free_result($result);
		return $a;
	}

	function fetchPOCs() { # Get pocFlow sensor to names
		$a = [];
		$result = pg_query($this->db, "SELECT sensor,name FROM pocFlow;");
		while ($row = pg_fetch_assoc($result)) {
			$a[$row['sensor']] = $row['name'];
		}
		pg_free_result($result);
		return $a;
	}

	function fetchSimulation() { # Determine if controllers are running in simulation mode
		$result = pg_query($this->db, "SELECT qSimulate FROM simulate;");
		$row = pg_fetch_assoc($result);
		pg_free_result($result);
		return $row != NULL and $row['qsimulate'];
	}

	function fetchCurrent() {
		$result = pg_execute($this->db, "get_current", []);
		$row = pg_fetch_assoc($result); # Load the result
		if ($row == NULL) {
			return NULL;
		}
		pg_free_result($result);
		$row['volts'] = round($row['volts'] * 0.1, 1);
		$row['tcurrent'] = round($row['tcurrent']);
		return $row; # There should only be one row
	}

	function fetchFlow() {
		$result = pg_execute($this->db, "get_flow", []);
		$row = pg_fetch_assoc($result); # Load the result
		if ($row == NULL) {
			return NULL;
		}
		pg_free_result($result);
		$row['flow'] = round($row['flow'], 1);
		$row['tflow'] = round($row['tflow']);
		return $row; # There should only be one row
	}

	function fetchNumberOn() {
		$result = pg_execute($this->db, "get_nOn", []);
		$nOn = pg_fetch_assoc($result); # Load the result
		if ($nOn == NULL) {
			return NULL;
		}
		pg_free_result($result);
		$result = pg_execute($this->db, "get_nPending", []);
		$nPending = pg_fetch_assoc($result); # Load the result
		return array_merge($nOn, $nPending); 
	}

	function fetchInitial() {
		$a = array_merge(
			$this->fetchCurrent(), 
			$this->fetchFlow(),
			$this->fetchNumberOn());
		$a['controllers'] = $this->fetchControllers();
		$a['pocs'] = $this->fetchPOCs();
		$a['simulation'] = $this->fetchSimulation();
		return json_encode($a);
	}

	function notifications() {
		return pg_get_notify($this->db);
	}
}

$a = new Status("irrigation");

echo "data: " . $a->fetchInitial() . "\n\n";
$tPrevious = time(); # Current time
while (True) { # Wait forever
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	$notify = $a->notifications();
	if (!$notify) {
		if ($tPrevious < (time() - 50)) { # Every 60 seconds there is a timeout
			echo json_encode($a->fetchNumberOn()) . "\n";
			flush();
			$tPrevious = time(); # Current time
		} else {
			sleep(1); # Wait a second before checking on notifications again
		}
	} else {
		$msg = $notify['message'];
		$result = NULL;
		if ($msg == 'currentlog_update') {
			$result = $a->fetchCurrent();
		} else if ($msg == 'sensorlog_update') {
			$result = $a->fetchFlow();
		} else {
			$result = $a->fetchNumberOn();
			$tPrevious = time();
		}
		echo "data: " . json_encode($result) . "\n\n";
		$tPrevious = time(); # Current time
	}
}
?>
