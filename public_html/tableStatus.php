<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

function mkMsg(bool $q, string $msg) {
	return "data: " .  json_encode(["success" => $q, "message" => $msg]) . "\n\n";
}

function tableInfo($db, $name) {
	$sql = 'SELECT * FROM tableInfo WHERE tbl=? ORDER BY displayOrder;';
	return $db->loadRows($sql, [$name]);
}

function tableRows($db, $name) {
	$sql = "SELECT * FROM $name ORDER BY grp,sortOrder;";
	return $db->loadRows($sql, []);
}

if (empty($_GET['tbl'])) {exit(mkMsg(false, 'No tbl parameter supplied'));}

require_once 'php/DB1.php';

$tbl = $_GET['tbl'];
if (!$db->tableExists($tbl)) {exit(mkMsg(false, "Table, $tbl, does not exist"));}

$db->listen(strtolower($tbl) . "_updated");

$info = array();
$info['info'] = tableInfo($db, $tbl);
$info['data'] = tableRows($db, $tbl);

while (True) { # Wait forever
	echo "data: " . json_encode($info) . "\n\n";
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	// Connections time out at ~60 seconds, so send a burp every ~55 seconds
	$notifications = $db->notifications(55000); 
	if ($notifications == false) { // no notifications
		$info = ['burp' => 0];
	} else { // notifications
		$info = ['data' => tableRows($db, $tbl)];
	}
}
?>
