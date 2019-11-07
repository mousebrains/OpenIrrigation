<?php
// Turn POCs on/off, clear all pending actions, or shut everything off

require_once 'php/DB1.php';

function mkMsg(bool $flag, string $msg) {return json_encode(['success'=>$flag, 'message'=>$msg]);}
function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}

if (empty($_POST['poc'])) exit(mkMsg(false, 'No POC supplied'));
$poc = $_POST['poc'];
$dt = 60;
if ($db->query("SELECT poc_off(?,?)", [$poc, $dt])) 
	exit(mkMsg(true, "Turned POC($poc) off for $dt minutes"));
echo dbMsg($db, "Failed to turn off POC($poc) for $dt minutes");
?>
