<?php
// shut everything off

require_once 'php/DB1.php';

if ($db->query("SELECT manual_all_off();"))
	exit(json_encode(['success'=>true, 'message'=>"Turned all valves off"]));
echo json_encode(['success'=>true, 'message'=>"Failed to turn all valves off, " . $db->getError()]);
?>
