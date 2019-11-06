<?php
// Turn off an active valve from monitor.php

require_once 'php/DB1.php';

function mkMsg(bool $flag, string $msg) {return json_encode(['success'=>$flag, 'message'=>$msg]);}
function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}

if (empty($_POST['id'])) exit(mkMsg(false, "No ID supplied."));
$id = $_POST['id'];

if ($db->query('SELECT manual_off(?);', [$id])) {
	exit(mkMsg(true, "Turned Valve $id off"));
}
echo dbMsg($db, "Failed to turn valve($id) off");
?>
