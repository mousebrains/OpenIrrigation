<?php
// Remove an pending record from action

require_once 'php/DB1.php';

function mkMsg(bool $flag, string $msg) {return json_encode(['success'=>$flag, 'message'=>$msg]);}
function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}

if (empty($_POST['id'])) exit(mkMsg(false, "No ID supplied."));
$id = $_POST['id'];

if ($db->query('DELETE FROM action WHERE id=($1) AND (cmdOn IS NOT NULL);', [$id])) 
	exit(mkMsg(true, "Removed pending record, $id, from actions"));

echo dbMsg($db, "Failed to remove pending record, $id");
?>
