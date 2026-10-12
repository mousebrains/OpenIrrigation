<?php
// Remove all pending actions

require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

try {
	$n = $db->query("DELETE FROM action WHERE cmdOn IS NOT NULL;")->rowCount();
} catch (PDOException $e) {
	exit($db->errMsg($e, "Failed to remove all pending actions"));
}
echo $db->mkMsg(true, "Removed all pending actions ($n)");
