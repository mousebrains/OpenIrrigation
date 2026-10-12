<?php
// Turn off an active valve from monitor.php

require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

$id = $_POST['id'] ?? null;
if (!is_string($id) || $id === '') exit($db->mkMsg(false, "No ID supplied."));
if (!ctype_digit($id)) exit($db->mkMsg(false, "Invalid ID"));

try {
	$db->query('SELECT manual_off(?);', [$id]);
} catch (PDOException $e) {
	exit($db->errMsg($e, "Failed to turn valve($id) off"));
}
echo $db->mkMsg(true, "Turned Valve $id off");
