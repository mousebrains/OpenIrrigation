<?php
// form submission from index.php

require_once 'php/DB1.php';

function mkMsg(bool $flag, $msg) {return json_encode(['success'=>$flag, 'message'=>$msg]);}
function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}

function chgLog($db, $addr, string $msg) {
	$sql = "INSERT INTO changeLog (ipAddr,description) VALUES(?,?);";
	$stmt = $db->prepare($sql);
	$stmt->execute([$addr, $msg]);
}

$addr = array_key_exists("REMOTE_ADDR", $_SERVER) ? $_SERVER["REMOTE_ADDR"] : "GotMe";

if (empty($_POST['id'])) {
	chgLog($db, $addr, "No id supplied");
	exit(mkMsg(false, "No ID supplied."));
}

$id = $_POST['id'];

if (array_key_exists('poc', $_POST)) { // work on a POC
	$poc = $_POST['poc'];
	if (array_key_exists('time', $_POST)) { // Turn a master valve on
		$dt = $_POST['time'];
		if ($db->query('SELECT poc_off(?,?);', [$poc, $dt])) {
			chgLog($db, $addr, "Turned on POC $poc for $dt minutes");
			exit(mkMsg(true, "Turned POC $poc off for $dt minutes"));
		}
		chgLog($db, $addr, "Failed to turn off POC $poc for $dt minutes");
		exit(dbMsg($db, "Failed to turn POC($poc) off for $dt minutes"));
	}
	if ($db->query('SELECT poc_on(?)', [$poc])) {
		chgLog($db, $addr, "Turned on POC $poc");
		exit(mkMsg(true, "Turned POC $poc on"));
	}
	chgLog($db, $addr, "Failed to turn off POC $poc");
	exit(dbMsg($db, "Failed to turn POC($poc) off"));
}

if (array_key_exists('time', $_POST)) { // Turn a valve on
	$dt = $_POST['time'];
	if ($db->query('SELECT manual_on(?,?);', [$id, $dt])) {
		chgLog($db, $addr, "Turned on valve($id) for $dt minutes");
		exit(mkMsg(true, "Turned Valve $id on for $dt minutes"));
	}
	chgLog($db, $addr, "Failed to turn on valve($id) for $dt minutes");
	exit(dbMsg($db, "Failed to turn valve($id) on for $dt minutes"));
}

if ($db->query('SELECT manual_off(?);', [$id])) {
	chgLog($db, $addr, "Turned off valve($id)");
	exit(mkMsg(true, "Turned Valve $id off"));
}
chgLog($db, $addr, "Failed to turn off valve($id)");
echo dbMsg($db, "Failed to turn valve($id) off");
?>
