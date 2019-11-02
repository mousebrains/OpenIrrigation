<?php
// Remove an pending record from action

if (empty($_POST['id'])) {
	echo json_encode(['success' => false, 'message' => 'No ID supplied']);
} else { // I have an ID so drop the action row
	$msg = '';
	$flag = true;
	$name= 'irrigation';
	$db = pg_connect("dbname=$name");
	$sql = 'DELETE FROM action WHERE id=($1) AND (cmdOn IS NOT NULL);';
	if (pg_query_params($db, $sql, [$_POST['id']])) {
		$msg = 'Removed ' . $_POST['id'];
	} else { // Failed for some reason
		$msg = pg_last_error($db);
		$flag = false;
	}
	pg_close($db);
	echo json_encode(['success' => flag, 'message' => msg]);
}
?>
