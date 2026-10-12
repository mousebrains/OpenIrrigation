<?php
// form submission from index.php

require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

const MAX_RUN_MINUTES = 300; // Same as the form's max='300' in js/index.js

// The posted run time in minutes, 0 < minutes <= MAX_RUN_MINUTES, else exit
function runMinutes(DB $db): float {
	$dt = $_POST['time'];
	if (!is_string($dt) || !is_numeric($dt)) exit($db->mkMsg(false, "Invalid time value"));
	$minutes = (float) $dt;
	if (!($minutes > 0 && $minutes <= MAX_RUN_MINUTES))
		exit($db->mkMsg(false, "Run time must be more than 0 and at most "
			. MAX_RUN_MINUTES . " minutes"));
	return $minutes;
}

$id = $_POST['id'] ?? null;
if (!is_string($id) || $id === '') exit($db->mkMsg(false, "No ID supplied"));
if (!ctype_digit($id)) exit($db->mkMsg(false, "Invalid ID"));

if (array_key_exists('poc', $_POST)) { // work on a POC
	$poc = $_POST['poc'];
	if (!is_string($poc) || !ctype_digit($poc)) exit($db->mkMsg(false, "Invalid POC ID"));
	if (array_key_exists('time', $_POST)) { // Turn a master valve off
		$dt = runMinutes($db);
		try {
			$db->query('SELECT poc_off(?,?);', [$poc, $dt]);
		} catch (PDOException $e) {
			exit($db->errMsg($e, "Failed to turn POC $poc off for $dt minutes"));
		}
		exit($db->mkMsg(true, "Turned POC $poc off for $dt minutes"));
	}
	try {
		$db->query('SELECT poc_on(?)', [$poc]);
	} catch (PDOException $e) {
		exit($db->errMsg($e, "Failed to turn on POC $poc"));
	}
	exit($db->mkMsg(true, "Turned on POC $poc"));
}

if (array_key_exists('time', $_POST)) { // Turn a valve on
	$dt = runMinutes($db);
	try {
		$db->query('SELECT manual_on(?,?);', [$id, $dt]);
	} catch (PDOException $e) {
		exit($db->errMsg($e, "Failed to turn valve $id on for $dt minutes"));
	}
	exit($db->mkMsg(true, "Turned valve $id on for $dt minutes"));
}

try {
	$db->query('SELECT manual_off(?);', [$id]);
} catch (PDOException $e) {
	exit($db->errMsg($e, "Failed to turn valve $id off"));
}
echo $db->mkMsg(true, "Turned Valve $id off");
