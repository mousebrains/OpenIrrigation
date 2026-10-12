<?php
// delete a row from a table
require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

$tblParam = $_POST['tableName'] ?? null;
$id = $_POST['id'] ?? null;
if (!is_string($tblParam) || $tblParam === '')
	exit($db->mkMsg(false, 'No table name supplied'));
if (!is_string($id) || $id === '') exit($db->mkMsg(false, 'No row id supplied'));
if (!ctype_digit($id)) exit($db->mkMsg(false, "Invalid row ID"));

try {
	$tbl = $db->tableName($tblParam);
	if ($tbl === null) exit($db->mkMsg(false, "Table, $tblParam, is not editable"));
	$canHide = array_key_exists('qhide', $db->tableColumns($tbl));

	$sql = "DELETE FROM " . $db->quoteIdent($tbl) . " WHERE id=?;";
	try {
		$n = $db->query($sql, [$id])->rowCount();
	} catch (PDOException $e) {
		if (!is_array($e->errorInfo) || $e->errorInfo[0] !== '23503') throw $e;
		// foreign_key_violation: other rows (runs, history, ...) refer to it
		[, $detail] = DB::pgMessage($e);
		exit($db->mkMsg(false, "$tbl id=$id is in use, so it was not deleted"
			. ($detail === '' ? '' : " ($detail)")
			. ($canHide ? "; hide it instead of deleting it" : "")));
	}
} catch (PDOException $e) {
	exit($db->errMsg($e, "Deletion of $tblParam id=$id failed"));
}

if ($n === 0) exit($db->mkMsg(false, "No row with id=$id in $tbl"));
echo $db->mkMsg(true, "Deleted from $tbl id=$id okay");
