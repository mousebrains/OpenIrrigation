<?php
// insert a row into a table
require_once 'php/DB1.php';

function mkMsg(bool $q, string $msg) {return json_encode(["success" => $q, "message" => $msg]);}
function dbMsg(string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}


if (empty($_POST['tableName'])) exit(mkMsg(false, 'No table name supplied'));

$tbl = $_POST['tableName'];
if (!$db->tableExists($tbl)) exit(mkMsg(false, "Table, $tbl, does not exist"));

$cols = $db->tableColumns($tbl);
$keys = array();
$markers = array();
$vals = array();
foreach ($cols as $key) {
	if (array_key_exists($key, $_POST)) {
		array_push($keys, $key);
		array_push($markers, '?');
		array_push($vals, $_POST[$key] == '' ? null : $_POST[$key]);
	}
}

if (empty($vals)) exit(mkMsg(false, "No columns found"));

$sql = "INSERT INTO $tbl (" . implode(',', $keys) . ") VALUES (" . implode(',', $markers) . ");";

// Insert into primary table
if (!$db->query($sql, $vals)) exit(dbMsg('Insertion failed'));

// Check if secondary tables exist for this table
$sql = "SELECT col,secondaryKey,secondaryValue FROM tableInfo"
       . " WHERE tbl=? AND secondaryKey IS NOT NULL;";
$sec = $db->loadRows($sql, [$tbl]);

if (!empty($sec)) {
	$sql = "SELECT id FROM $tbl"
		. " WHERE (" . implode(',', $keys) . ")=(" . implode(',', $markers) . ");";
	$rows = $db->loadRows($sql, $vals);
	if (empty($rows)) exit(mkMsg(false, "Unable to get table id for secondary entries, $tbl"));
	$id = $rows[0]['id'];
	foreach($sec as $row) {
		$stbl = $row['col'];
		$key0 = $row['secondarykey'];
		$key1 = $row['secondaryvalue'];
		if (!empty($_POST[$stbl])) { // Something to be stored
			$sql = "INSERT INTO $stbl ($key0, $key1) VALUES(?,?);";
			foreach ($_POST[$stbl] as $sid) {
				if (!$db->query($sql, [$id, $sid])) {
					exit(dbMsg("Failed to insert secondary"));
				}
			}
		}
	}
}

echo mkMsg(true, "Inserted into $tbl");
?>
