<?php
// form submission from index.php

require_once 'php/DB1.php';

if (empty($_POST['id'])) exit($db->mkMsg(false, "No ID supplied"));

$id = $_POST['id'];

if (array_key_exists('poc', $_POST)) { // work on a POC
	$poc = $_POST['poc'];
	if (array_key_exists('time', $_POST)) { // Turn a master valve on
		$dt = $_POST['time'];
		if ($db->query('SELECT poc_off(?,?);', [$poc, $dt]))
			exit($db->mkMsg("Turned POC $poc off for $dt minutes"));
		exit($db->dbMsg("Failed to turn POC $poc off for $dt minutes"));
	}
	if ($db->query('SELECT poc_on(?)', [$poc])) exit($db->mkMsg(true, "Turned on POC $poc"));
	exit($db->dbMsg("Failed to turn POC $poc off"));
}

if (array_key_exists('time', $_POST)) { // Turn a valve on
	$dt = $_POST['time'];
	if ($db->query('SELECT manual_on(?,?);', [$id, $dt]))
		exit($db->mkMsg(true, "Turned valve $id on for $dt minutes"));
	exit($db->dbMsg("Failed to turn valve $id on for $dt minutes"));
}

if ($db->query('SELECT manual_off(?);', [$id])) exit($db->mkMsg(true, "Turned Valve $id off"));
echo $db->dbMsg("Failed to turn valve $id off");
?>
