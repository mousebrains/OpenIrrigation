<?php
// update a row in a table
require_once 'php/DB1.php';

function mkMsg(bool $q, string $msg) {
	return json_encode(["success" => $q, "message" => $msg]);
}

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

$sql = "UPDATE $tbl SET " . implode(',', $keys) . " WHERE id=?;";

array_push($vals, $id);
if ($db->query($sql, $vals)) exit(mkMsg(true, 'Update okay'));
echo mkMsg(false, 'Insertion failed ' . $db->getError());
?>
