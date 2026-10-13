<?php
// Remove an pending record from action

require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

$id = $_POST['id'] ?? null;
if (!is_string($id) || $id === '') exit($db->mkMsg(false, "No ID supplied"));
if (!ctype_digit($id)) exit($db->mkMsg(false, "Invalid ID"));

try {
	$n = $db->query('DELETE FROM action WHERE id=(?) AND (cmdOn IS NOT NULL);', [$id])->rowCount();
} catch (PDOException $e) {
	exit($db->errMsg($e, "Failed to remove pending record, $id"));
}
if ($n === 0) exit($db->mkMsg(false, "Pending record, $id, not found; it has already started or been removed"));
echo $db->mkMsg(true, "Removed pending record, $id, from actions");
