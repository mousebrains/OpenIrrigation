<?php
// Remove all pending actions

require_once 'php/DB1.php';

if ($db->query("DELETE FROM action WHERE cmdOn IS NOT NULL;"))
	exit(json_encode(['success'=>true, 'message'=>"Removed all pending actions"]));
echo json_encode(['success'=>false,
	'messge'=>"Failed to remove all pending actions, " . $db->getError()]);
?>
