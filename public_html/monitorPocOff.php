<?php
// Turn POCs on/off, clear all pending actions, or shut everything off

require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

$poc = $_POST['poc'] ?? null;
if (!is_string($poc) || $poc === '') exit($db->mkMsg(false, 'No POC supplied'));
if (!ctype_digit($poc)) exit($db->mkMsg(false, 'Invalid POC'));

$dt = 60;

try {
	$db->query("SELECT poc_off(?,?)", [$poc, $dt]);
} catch (PDOException $e) {
	exit($db->errMsg($e, "Failed to turn off POC($poc) for $dt minutes"));
}
echo $db->mkMsg(true, "Turned POC($poc) off for $dt minutes");
