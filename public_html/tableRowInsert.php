<?php
// insert a row into a table
require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

$tblParam = $_POST['tableName'] ?? null;
if (!is_string($tblParam) || $tblParam === '')
	exit($db->mkMsg(false, 'No table name supplied'));

try {
	$tbl = $db->tableName($tblParam);
	if ($tbl === null) exit($db->mkMsg(false, "Table, $tblParam, is not editable"));

	$keys = [];
	$markers = [];
	$vals = [];
	$logVals = [];

	foreach ($db->tableColumns($tbl) as $key => $type) {
		if (array_key_exists($key, $_POST)) {
			if (!is_string($_POST[$key])) exit($db->mkMsg(false, "Invalid value for $key"));
			$val = $_POST[$key] === '' ? NULL : $_POST[$key];
			$logVals[] = ($type === 'password' && $val !== NULL) ? '(set)' : $val;
			if ($type === 'password' && $val !== NULL) $val = password_hash($val, PASSWORD_DEFAULT);
			$keys[] = $db->quoteIdent($key);
			$markers[] = '?';
			$vals[] = $val;
		}
	}

	if (empty($vals)) exit($db->mkMsg(false, "No columns found in $tbl"));

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

	$db->beginTransaction();

	$sql = "INSERT INTO " . $db->quoteIdent($tbl) . " (" . implode(',', $keys) . ") VALUES (" . implode(',', $markers) . ")"
		. " RETURNING id;";
	$id = $db->query($sql, $vals)->fetchColumn();

	$comment = ["Inserted into $tbl (" . implode(',', $keys) . ')->(' . implode(',', $logVals) . ')'];

	foreach ($sec as $row) {
		$stbl = $db->quoteIdent($row['col']);
		$key0 = $db->quoteIdent($row['secondarykey']);
		$key1 = $db->quoteIdent($row['secondaryvalue']);
		$postKey = $row['col'];
		if (!empty($_POST[$postKey])) { // Something to be stored
			$sql = "INSERT INTO $stbl ($key0, $key1) VALUES(?,?);";
			foreach ($_POST[$postKey] as $sid) {
				$db->query($sql, [$id, $sid]);
				$comment[] = "Inserted into $stbl $key0=$id $key1=$sid";
			}
		}
	}

	// The changeLog records commit, or roll back, with the change itself
	foreach ($comment as $msg) $db->audit($msg);

	$db->commit();
} catch (PDOException $e) {
	exit($db->errMsg($e, "Insert into $tblParam failed"));
}

echo $db->mkMsg(true, "Inserted into $tbl");
