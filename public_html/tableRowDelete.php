<?php
// delete a row into a table
require_once 'php/DB1.php';

if (empty($_POST['tableName'])) exit($db->mkMsg(false, 'No table name supplied'));
if (empty($_POST['id'])) exit($db->mkMsg(false, 'No row id supplied'));

$tbl = $_POST['tableName'];
$id = $_POST['id'];

if (!$db->tableExists($tbl)) exit($db->dbMsg("Table, $tbl, does not exist"));

$sql = "DELETE FROM " . $db->quoteIdent($tbl) . " WHERE id=?;";
if (!$db->query($sql, [$id])) exit($db->dbMsg("Deletion of id=$id failed"));
echo $db->mkMsg(true, "Deleted from $tbl id=$id okay");
?>
