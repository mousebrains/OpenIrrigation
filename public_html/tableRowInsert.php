<?php
// insert a row into a table
require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

if (empty($_POST['tableName']) || !is_string($_POST['tableName']))
	exit($db->mkMsg(false, 'No table name supplied'));

$tbl = $_POST['tableName'];
if (!$db->tableExists($tbl)) exit($db->mkMsg(false, "Table, $tbl, does not exist"));

$cols = $db->tableColumns($tbl);
$keys = [];
$markers = [];
$vals = [];

foreach ($cols as $key) {
	if (array_key_exists($key, $_POST)) {
		if (!is_string($_POST[$key])) exit($db->mkMsg(false, "Invalid value for $key"));
		$val = $_POST[$key] === '' ? NULL : $_POST[$key];
		$keys[] = $db->quoteIdent($key);
		$markers[] = '?';
		$vals[] = $val;
	}
}

if (empty($vals)) exit($db->mkMsg(false, "No columns found in $tbl"));

$db->beginTransaction();

$sql = "INSERT INTO " . $db->quoteIdent($tbl) . " (" . implode(',', $keys) . ") VALUES (" . implode(',', $markers) . ")"
	. " RETURNING id;";

$stmt = $db->prepare($sql); // Prepare the statement
if ($stmt === false) exit($db->dbMsg("Error preparing $sql"));
if (!$stmt->execute($vals)) exit($db->dbMsg("Error executing $sql"));
$id = $stmt->fetch(PDO::FETCH_NUM)[0];

$comment = ["Inserted into $tbl (" . implode(',', $keys) . ')->(' . implode(',', $vals) . ')'];

// Check if secondary tables exist for this table
$sql = "SELECT col,secondaryKey,secondaryValue FROM tableInfo"
       . " WHERE tbl=? AND secondaryKey IS NOT NULL;";
$sec = $db->loadRows($sql, [$tbl]);

if (!empty($sec)) {
	foreach($sec as $row) {
		$stbl = $db->quoteIdent($row['col']);
		$key0 = $db->quoteIdent($row['secondarykey']);
		$key1 = $db->quoteIdent($row['secondaryvalue']);
		$postKey = $row['col'];
		if (!empty($_POST[$postKey])) { // Something to be stored
			if (!is_array($_POST[$postKey])) exit($db->mkMsg(false, "Invalid secondary values"));
			$sql = "INSERT INTO $stbl ($key0, $key1) VALUES(?,?);";
			foreach ($_POST[$postKey] as $sid) {
				if (!$db->query($sql, [$id, $sid])) {
					exit($db->dbMsg("Failed to insert secondary"));
				}
				$comment[] = "Inserted into $stbl $key0=$id $key1=$sid";
			}
		}
	}
}

$db->commit();

echo $db->mkMsg(true, "Inserted into $tbl");

// Insert changeLog records
$db->beginTransaction();
$sql = 'INSERT INTO changeLog (ipAddr,description) VALUES (?,?);';
$stmt = $db->prepare($sql);
if ($stmt === false) exit($db->dbMsg("Error preparing $sql"));

foreach ($comment as $row) {
	if (!$stmt->execute([$_SERVER['REMOTE_ADDR'], $row]))
		exit($db->dbMsg("Error executing $sql"));
}
$db->commit();
