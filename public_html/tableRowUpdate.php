<?php
// update a row in a table
require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

$tblParam = $_POST['tableName'] ?? null;
$id = $_POST['id'] ?? null;
if (!is_string($tblParam) || $tblParam === '')
	exit($db->mkMsg(false, 'No table name supplied'));
if (!is_string($id) || $id === '') exit($db->mkMsg(false, 'No table row id supplied'));
if (!ctype_digit($id)) exit($db->mkMsg(false, "Invalid row ID"));

try {
	$tbl = $db->tableName($tblParam);
	if ($tbl === null) exit($db->mkMsg(false, "Table, $tblParam, is not editable"));

	$keys = [];
	$vals = [];
	$comment = [];

	foreach ($db->tableColumns($tbl) as $key => $type) {
		if (!array_key_exists($key, $_POST)) continue;
		if (!is_string($_POST[$key])) exit($db->mkMsg(false, "Invalid value for $key"));
		if ($type === 'password') {
			// The browser is never sent the stored value, so there is no
			// previous value to compare with: blank leaves it unchanged.
			if ($_POST[$key] === '') continue;
			$keys[] = $db->quoteIdent($key) . "=?";
			$vals[] = password_hash($_POST[$key], PASSWORD_DEFAULT);
			$comment[] = "In $tbl changed $key";
			continue;
		}
		$prevKey = $key . "Prev";
		if (!array_key_exists($prevKey, $_POST)) continue;
		if (!is_string($_POST[$prevKey])) exit($db->mkMsg(false, "Invalid value for $key"));
		if ($_POST[$key] === $_POST[$prevKey]) continue;
		$val = $_POST[$key] === '' ? NULL : $_POST[$key];
		$keys[] = $db->quoteIdent($key) . "=?";
		$vals[] = $val;
		$prevMsg = $_POST[$prevKey] === '' ? 'NULL' : $_POST[$prevKey];
		$valMsg = $val === NULL ? 'NULL' : $val;
		$comment[] = "In $tbl changed $key from $prevMsg to $valMsg";
	}

	// Secondary tables (e.g. a program's days of the week) for this table
	$sql = "SELECT col,secondaryKey,secondaryValue FROM tableInfo"
		. " WHERE tbl=? AND secondaryKey IS NOT NULL;";
	$sec = $db->loadRows($sql, [$tbl]);
	foreach ($sec as $row) {
		$postKey = $row['col'];
		if (!empty($_POST[$postKey]) && (!is_array($_POST[$postKey])
				|| count(array_filter($_POST[$postKey], 'is_string')) !== count($_POST[$postKey])))
			exit($db->mkMsg(false, "Invalid secondary values"));
	}

	$qPrimary = !empty($vals);
	$qSecondary = !empty($sec);
	if (!$qPrimary && !$qSecondary) exit($db->mkMsg(false, "No columns found to be updated"));

	$db->beginTransaction();

	if ($qPrimary) {
		$sql = "UPDATE " . $db->quoteIdent($tbl) . " SET " . implode(',', $keys) . " WHERE id=?;";
		$vals[] = $id; // For WHERE id=?
		$found = $db->query($sql, $vals)->rowCount() > 0;
	} else {
		$sql = "SELECT 1 FROM " . $db->quoteIdent($tbl) . " WHERE id=?;";
		$found = $db->query($sql, [$id])->fetchColumn() !== false;
	}
	if (!$found) {
		$db->rollback();
		exit($db->mkMsg(false, "No row with id=$id in $tbl"));
	}

	foreach ($sec as $row) { // Walk through any secondary tables
		$stbl = $db->quoteIdent($row['col']);
		$key0 = $db->quoteIdent($row['secondarykey']);
		$key1 = $db->quoteIdent($row['secondaryvalue']);
		$db->query("DELETE FROM $stbl WHERE $key0=?;", [$id]); // Remove current entries
		$comment[] = "Deleted $key0=$id row from $stbl";
		$postKey = $row['col'];
		if (!empty($_POST[$postKey])) { // Something to be stored
			$sql = "INSERT INTO $stbl ($key0, $key1) VALUES(?,?);";
			foreach ($_POST[$postKey] as $sid) {
				$db->query($sql, [$id, $sid]);
				$comment[] = "Insert into $stbl $key0=$id $key1=$sid";
			}
		}
	}

	if (!$qPrimary) {
		// The secondary was updated but the primary was not,
		// so send a notification for the primary
		$db->query("SELECT pg_notify(?,?);", [strtolower($tbl) . "_update", "$tbl UPDATE $id"]);
	}

	// The changeLog records commit, or roll back, with the change itself
	foreach ($comment as $msg) $db->audit($msg);

	$db->commit();
} catch (PDOException $e) {
	exit($db->errMsg($e, "Update of $tblParam id=$id failed"));
}

echo $db->mkMsg(true, "Updated $tbl");
