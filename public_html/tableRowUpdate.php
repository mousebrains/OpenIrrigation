<?php
// update a row in a table
require_once 'php/DB1.php';

if (empty($_POST['tableName'])) exit($db->mkMsg(false, 'No table name supplied'));
if (empty($_POST['id'])) exit($db->mkMsg(false, 'No table row id supplied'));

$tbl = $_POST['tableName'];
$id = $_POST['id'];

if (!$db->tableExists($tbl)) exit($db->dbMsg("Table, $tbl, does not exist"));

$cols = $db->tableColumns($tbl);
$keys = array();
$vals = array();
$comment = array();

foreach ($cols as $key) {
	$prevKey = $key . "Prev";
	if (array_key_exists($key, $_POST) 
		&& array_key_exists($prevKey, $_POST)
		&& ($_POST[$key] != $_POST[$prevKey])) {
		array_push($keys, "$key=?");
		array_push($vals, $_POST[$key]);
		array_push($comment, 
			"In $tbl changed $key from " . $_POST[$prevKey] . " to " . $_POST[$key]);
	}
}

$qPrimary = !empty($vals);
$qSecondary = false;

$db->beginTransaction();

if ($qPrimary) {
	$sql = "UPDATE $tbl SET " . implode(',', $keys) . " WHERE id=?;";
	array_push($vals, $id); // For WHERE id=?
	if (!$db->query($sql, $vals)) {
		exit($db->dbMsg('Insertion failed')); // Update failed, so don't do anything else
	}
}

// Check if secondary tables exist for this table
$sql = "SELECT col,secondaryKey,secondaryValue FROM tableInfo"
	. " WHERE tbl=? AND secondaryKey IS NOT NULL;";
foreach ($db->loadRows($sql, [$tbl]) as $row) { // Walk through any secondary tables
	$stbl = $row['col'];
	$key0 = $row['secondarykey'];
	$key1 = $row['secondaryvalue'];
	$sql = "DELETE FROM $stbl WHERE $key0=?;"; // Remove current entries
	if (!$db->query($sql, [$id])) exit($db->dbMsg('Delete secondary'));
	array_push($comment, "Deleted $key0=$id row from $stbl");
	if (!empty($_POST[$stbl])) { // Something to be stored
		$qSecondary = true;
		$sql = "INSERT INTO $stbl ($key0, $key1) VALUES(?,?);";
		foreach ($_POST[$stbl] as $sid) {
			if (!$db->query($sql, [$id, $sid])) {
				exit($db->dbMsg("Failed to insert secondary"));
			}
			array_push($comment, "Insert into $stbl $key0=$id $key1=$sid");
		}
	}
}

$db->commit();

if (!$qPrimary && $qSecondary) {
	// The secondary was updated the but primary was not,
	// so send a notification for the primary
	$sql = "NOTIFY $tbl" . "_update,'$tbl UPDATE $id';";
	$db->query($sql);
}

if (!$qPrimary && !$qSecondary) exit($db->mkMsg(false, "No columns found to be updated"));

echo $db->mkMsg(true, "Updated $tbl");

// Insert changeLog records
$db->beginTransaction();
$sql = 'INSERT INTO changeLog (ipAddr,description) VALUES (?,?);';
$stmt = $db->prepare($sql);

foreach ($comment as $row) {
	if (!$stmt->execute([$_SERVER['REMOTE_ADDR'], $row]))
		exit($db->dbMsg("Error executing $sql"));
}
$db->commit();
?>
