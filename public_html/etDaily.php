<?php
// Grab a column of data for et information

function mkMsg(bool $flag, string $msg) {
	return json_encode(['success' => $flag, 'message' => $msg]);
}

require_once 'php/DB1.php';

if (empty($_POST['codigo'])) exit(mkMsg(false, "No codigo supplied"));
if (!is_numeric($_POST['codigo'])) exit(mkMsg(false, "Invalid codigo"));
if (empty($_POST['sdate'])) exit(mkMsg(false, "No sdate supplied"));
if (!is_numeric($_POST['sdate'])) exit(mkMsg(false, "Invalid start date"));
if (empty($_POST['edate'])) $_POST['edate'] = time();
if (!is_numeric($_POST['edate'])) exit(mkMsg(false, "Invalid end date"));

$sql = "SELECT t,value FROM ET"
	. " WHERE code=?"
	. " AND t>=to_timestamp(?)::date"
	. " AND t<=to_timestamp(?)::date"
	. " ORDER BY t DESC;";
$rows = $db->loadRowsNum($sql, [$_POST['codigo'], $_POST['sdate'], $_POST['edate']]);
echo json_encode($rows);
?>
