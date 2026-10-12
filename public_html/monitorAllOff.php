<?php
// shut everything off

require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

try {
	$db->query("SELECT manual_all_off();");
} catch (PDOException $e) {
	exit($db->errMsg($e, "Failed to turn off all valves"));
}
echo $db->mkMsg(true, "Turned off all valves");
