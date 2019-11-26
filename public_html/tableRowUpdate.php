<?php
// update a row in a table
require_once 'php/DB1.php';

function mkMsg(bool $q, string $msg) {return json_encode(["success" => $q, "message" => $msg]);}
function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}

if (empty($_POST['tableName'])) exit(mkMsg(false, 'No table name supplied'));
if (empty($_POST['id'])) exit(mkMsg(false, 'No table row id supplied'));

$tbl = $_POST['tableName'];
$id = $_POST['id'];

if (!$db->tableExists($tbl)) exit(mkMsg(false, "Table, $tbl, does not exist"));

$cols = $db->tableColumns($tbl);
$keys = array();
$vals = array();
foreach ($cols as $key) {
	$prevKey = $key . "Prev";
	if (array_key_exists($key, $_POST) 
		&& array_key_exists($prevKey, $_POST)
		&& ($_POST[$key] != $_POST[$prevKey])) {
		array_push($keys, "$key=?");
		array_push($vals, $_POST[$key]);
	}
}

if (empty($vals)) exit(mkMsg(false, "No columns found to be updated"));

$db->beginTransaction();

$sql = "UPDATE $tbl SET " . implode(',', $keys) . " WHERE id=?;";
array_push($vals, $id); // For WHERE id=?

if (!$db->query($sql, $vals)) echo dbMsg($db, 'Insertion failed');

// Check if secondary tables exist for this table
$sql = "SELECT col,secondaryKey,secondaryValue FROM tableInfo"
	. " WHERE tbl=? AND secondaryKey IS NOT NULL;";
foreach ($db->loadRows($sql, [$tbl]) as $row) { // Walk through any secondary tables
	$stbl = $row['col'];
	$key0 = $row['secondarykey'];
	$key1 = $row['secondaryvalue'];
	$sql = "DELETE FROM $stbl WHERE $key0=?;"; // Remove current entries
	if (!$db->query($sql, [$id])) exit(dbMsg($db, 'Delete secondary'));
	if (!empty($_POST[$stbl])) { // Something to be stored
		$sql = "INSERT INTO $stbl ($key0, $key1) VALUES(?,?);";
		foreach ($_POST[$stbl] as $sid) {
			if (!$db->query($sql, [$id, $sid])) {
				exit(dbMsg($db, "Failed to insert secondary"));
			}
		}
	}
}

$db->commit();

echo mkMsg(true, "Updated $tbl");
?>
