<?php
// Remove an pending record from action

$name= 'irrigation';
$flag = true;
$msg = '';
$sql = '';
$args = [];

if (empty($_POST['action'])) {
	$flag = false;
	$msg = 'No action supplied';
} else if ($_POST['action'] == 'pocOff') {
	if (empty($_POST['poc'])) {
		$flag = false;
		$msg = 'No poc supplied';
	} else {
		$sql = 'SELECT poc_off($1,$2);';
		$args = [$_POST['poc'], 60];
		$msg = 'Turned POC(' . $args[0] . ') Off for ' . $args[1] . ' mintues';
	}
} else if ($_POST['action'] == 'clearAll') {
	$sql = 'DELETE FROM action WHERE cmdOn IS NOT NULL;';
	$msg = 'Removed all pending actions';
} else if ($_POST['action'] == 'allOff') {
	$sql = 'SELECT manual_all_off();';
	$msg = 'Turned off all valves';
} else {
	$flag = false;
	$msg = 'Unrecognized action ' . $_POST['action'];
}

if ($sql != '') {
	$db = pg_connect("dbname=$name");
	if (!pg_query_params($db, $sql, $args)) {
		$msg = pg_last_error($db);
		$flag = false;
	}
	pg_close($db);
}

echo json_encode(['success' => $flag, 'message' => $msg]);
?>
