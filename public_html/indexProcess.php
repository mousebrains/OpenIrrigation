<?php
// form submission from index.php

require_once 'php/DB1.php';

function mkMsg(bool $flag, string $msg) {return json_encode(['success'=>$flag, 'message'=>$msg]);}
function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}

if (empty($_POST['id'])) exit(mkMsg(false, "No ID supplied."));
$id = $_POST['id'];

if (array_key_exists('poc', $_POST)) { // work on a POC
	$poc = $_POST['poc'];
	if (array_key_exists('time', $_POST)) { // Turn a master valve on
		$dt = $_POST['time'];
		if ($db->query('SELECT poc_off(?,?);', [$poc, $dt])) {
			exit(mkMsg(true, "Turned POC $poc off for $dt minutes"));
		}
		exit(dbMsg($db, "Failed to turn POC($poc) off for $dt minutes"));
	}
	if ($db->query('SELECT poc_on(?)', [$poc])) {
		exit(mkMsg(true, "Turned POC $poc on"));
	}
	exit(dbMsg($db, "Failed to turn POC($poc) off"));
}

if (array_key_exists('time', $_POST)) { // Turn a valve on
	$dt = $_POST['time'];
	if ($db->query('SELECT manual_on(?,?);', [$id, $time])) {
		exit(mkMsg(true, "Turned Valve $id on for $dt minutes"));
	}
	exit(dbMsg($db, "Failed to turn valve($id) on for $dt minutes"));
}

if ($db->query('SELECT manual_off(?);', [$id])) {
	exit(mkMsg(true, "Turned Valve $id off"));
}
echo dbMsg($db, "Failed to turn valve($id) off");
?>
