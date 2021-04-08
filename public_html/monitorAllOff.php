<?php
// shut everything off

require_once 'php/DB1.php';

if ($db->query("SELECT manual_all_off();")) exit($db->mkMsg(true, "Turned off all valves"));
echo $db->dbMsg("Failed to turn off all valves");
?>
