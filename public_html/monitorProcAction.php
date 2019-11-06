<?php
// Turn POCs on/off, clear all pending actions, or shut everything off

require_once 'php/DB1.php';

function mkMsg(bool $flag, string $msg) {return json_encode(['success'=>$flag, 'message'=>$msg]);}
function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}

if (empty($_POST['action'])) exit(mkMsg(false, "No action supplied."));

$action = $_POST['action'];

if ($action == 'pocOff') {
	if (empty($_POST['poc'])) exit(mkMsg(false, 'No POC supplied'));
	$poc = $_POST['poc'];
	$dt = 60;
	if ($db->query("SELECT poc_off(?,?)", [$poc, $dt])) 
		exit(mkMsg(true, "Turned POC($poc) off for $dt minutes"));
	exit(dbMsg($db, "Failed to turn off POC($poc) for $dt minutes"));
}

if ($action == 'clearAll') {
	if ($db->query("DELETE FROM action WHERE cmdOn IS NOT NULL;")) 
		exit(mkMsg(true, "Removed all pending actions"));
	exit(dbMsg($db, "Failed to remove all pending actions"));
} 

if ($action == 'allOff') {
	$sql = "SELECT manual_all_off();";
	$args = [];
	$msg = "Turned off all valves";
	if ($db->query("SELECT manual_all_off();")) 
		exit(mkMsg(true, "Turned all valves off"));
	exit(dbMsg($db, "Failed to turn all valves off"));
}

exit(mkMsg(false, "Unrecognized action $action"));
?>
