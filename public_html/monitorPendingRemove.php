<?php
// Remove an pending record from action

require_once 'php/DB1.php';

if (empty($_POST['id'])) exit($db->mkMsg(false, "No ID supplied"));

$id = $_POST['id'];

if ($db->query('DELETE FROM action WHERE id=(?) AND (cmdOn IS NOT NULL);', [$id]))
	exit($db->mkMsg(true, "Removed pending record, $id, from actions"));

echo $db->mkMsg(false, "Failed to remove pending record, $id");
?>
