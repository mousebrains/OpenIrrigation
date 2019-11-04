<?php
// insert a row into a table
require_once 'php/DB1.php';

function mkMsg(bool $q, string $msg) {
	return json_encode(["success" => $q, "message" => $msg]);
}

if (empty($_POST['tableName'])) exit(mkMsg(false, 'No table name supplied'));

$tbl = $_POST['tableName'];
if (!$db->tableExists($tbl)) exit(mkMsg(false, "Table, $tbl, does not exist"));

$cols = $db->tableColumns($tbl);
$markers = array();
$vals = array();
foreach ($cols as $key) {
	if (array_key_exists($key, $_POST)) {
		array_push($markers, '?');
		array_push($vals, $_POST[$key]);
	}
}

if (empty($vals)) exit(mkMsg(false, "No columns found"));

$sql = "INSERT INTO $tbl (" . implode(',', $cols) . ") VALUES (" . implode(',', $markers) . ");";

if ($db->query($sql, $vals)) exit(mkMsg(true, 'Insertion okay'));
echo mkMsg(false, 'Insertion failed ' . $db->getError());
?>
