<?php
// Grab a column of data for et information

function mkMsg(bool $flag, string $msg) {
	return json_encode(['success' => $flag, 'messge' => $msg]);
}

function dbMsg($db, string $msg) {return mkMsg(false, $msg . ", " . $db->lastError());}

require_once 'php/DB1.php';

$_POST['codigo'] = "69";
$_POST['sdate'] = time() - 20*86400;

if (empty($_POST['codigo'])) exit(mkMsg(false, "No codigo supplied"));
if (empty($_POST['sdate'])) exit(mkMsg(false, "No sdate supplied"));
if (empty($_POST['edate'])) $_POST['edate'] = time();

$sql = "SELECT t,value FROM ET"
	. " WHERE code=?"
	. " AND t>=to_timestamp(?)::date"
	. " AND t<=to_timestamp(?)::date"
	. " ORDER BY t DESC;";
$rows = $db->loadRowsNum($sql, [$_POST['codigo'], $_POST['sdate'], $_POST['edate']]);
echo json_encode($rows);
?>
