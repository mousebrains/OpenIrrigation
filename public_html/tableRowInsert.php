<?php
// insert a row into a table
require_once 'php/DB1.php';

function mkMsg(bool $q, string $msg) {return json_encode(["success" => $q, "message" => $msg]);}
function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->getError());}


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

$db->beginTransaction();

$sql = "INSERT INTO $tbl (" . implode(',', $keys) . ") VALUES (" . implode(',', $markers) . ")"
	. " RETURNING id;";

$stmt = $db->prepare($sql); // Prepare the statement
if ($stmt == false) exit(dbMsg($db, 'Error preparing $sql'));
if (!$stmt->execute($vals)) exit(mkMsg(false, "Error executing $sql, " . $stmt->errorInfo()));
$id = $stmt->fetch(PDO::FETCH_NUM)[0];

// Check if secondary tables exist for this table
$sql = "SELECT col,secondaryKey,secondaryValue FROM tableInfo"
       . " WHERE tbl=? AND secondaryKey IS NOT NULL;";
$sec = $db->loadRows($sql, [$tbl]);

if (!empty($sec)) {
	foreach($sec as $row) {
		$stbl = $row['col'];
		$key0 = $row['secondarykey'];
		$key1 = $row['secondaryvalue'];
		if (!empty($_POST[$stbl])) { // Something to be stored
			$sql = "INSERT INTO $stbl ($key0, $key1) VALUES(?,?);";
			foreach ($_POST[$stbl] as $sid) {
				if (!$db->query($sql, [$id, $sid])) {
					exit(dbMsg($db, "Failed to insert secondary"));
				}
			}
		}
	}
}

$db->commit();

echo mkMsg(true, "Inserted into $tbl, " . json_encode($a));
?>
