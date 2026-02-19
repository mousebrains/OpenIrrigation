<?php
// Remove all pending actions

require_once 'php/DB1.php';
$db = DB::getInstance();

if ($db->query("DELETE FROM action WHERE cmdOn IS NOT NULL;"))
	exit($db->mkMsg(true, "Removed all pending actions"));

echo $db->dbMsg("Failed to remove all pending actions");
?>
