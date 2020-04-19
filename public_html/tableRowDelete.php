<?php
// delete a row into a table
require_once 'php/DB1.php';

function mkMsg(bool $q, string $msg) {
	return json_encode(["success" => $q, "message" => $msg]);
}

if (empty($_POST['tableName'])) exit(mkMsg(false, 'No table name supplied'));
if (empty($_POST['id'])) exit(mkMsg(false, 'No row id supplied'));

$tbl = $_POST['tableName'];
$id = $_POST['id'];

if (!$db->tableExists($tbl)) exit(mkMsg(false, "Table, $tbl, does not exist"));

$sql = "DELETE FROM $tbl WHERE id=?;";
if (!$db->query($sql, [$id])) exit(mkMsg(false, "Deletion of id=$id failed " . $db->getError()));
echo mkMsg(true, "Deletion of id=$id okay");

// Insert changeLog records
$db->beginTransaction();
$sql = 'INSERT INTO changeLog (ipAddr,description) VALUES (?,?);';
$stmt = $db->prepare($sql);
if (!$stmt->execute([$_SERVER['REMOTE_ADDR'], "Deleted from $tbl where id=$id"])) {
	exit(mkMsg(false, "Error executing $sql, " . $stmt->errorInfo()));
}
$db->commit();
?>
