<?php
// Turn off an active valve from monitor.php

if (empty($_POST['id'])) {
	echo json_encode(['success' => false, 'message' => 'No ID supplied']);
} else { // I have an ID so turn it off
	$msg = '';
	$flag = true;
	$name= 'irrigation';
	$db = pg_connect("dbname=$name");
	if (pg_query_params($db, 'SELECT manual_off($1);', [$_POST['id']])) {
		$msg = 'Turned off ' . $_POST['id'];
	} else { // Failed for some reason
		$msg = pg_last_error($db);
		$flag = false;
	}
	pg_close($db);
	echo json_encode(['success' => flag, 'message' => msg]);
}
?>
