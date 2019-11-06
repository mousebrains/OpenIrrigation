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

function tableRows($db, $name, $orderBy) {
	$sql = "SELECT * FROM " . $name . $orderBy . ";";
	return $db->loadRows($sql, []);
}

function tableReference($db, $name) {
	$sql = "SELECT col,refTable,refKey,refLabel,refCriteria,refOrderBy"
		. " FROM tableInfo"
		. " WHERE tbl=? AND refTable IS NOT NULL;";
	$info = array();
	foreach ($db->loadRows($sql, [$name]) as $row) {
		$tbl = $row['reftable'];
		$col = $row['col'];
		$sql = "SELECT " . $row['refkey'] . " AS id," 
			. $row['reflabel'] . " AS name"
			. " FROM " . $tbl;
		if ($row['refcriteria'] != null) $sql .= " WHERE " . $row['refcriteria'];
		if ($row['reforderby'] != null) $sql .= " ORDER BY " . $row['reforderby'];
		$sql .= ";";
		$info[$col] = $db->loadRows($sql, []);
	}
	return $info;
}

function tableSecondary($db, $name) {
	$sql = "SELECT col,secondaryKey AS key0,secondaryValue AS key1 FROM tableInfo"
		. " WHERE tbl=? AND secondaryKey IS NOT NULL;";
	$info = array();
	foreach ($db->loadRows($sql, [$name]) as $row) {
		$col = $row['col'];
		$key0 = $row['key0'];
		$key1 = $row['key1'];
		$sql = "SELECT $key0,$key1 FROM $col;";
		$info[$col] = [];
		foreach ($db->loadRows($sql, []) as $a) {
			$id = $a[$key0];
			if (!array_key_exists($id, $info[$col])) $info[$col][$id] = array();
			array_push($info[$col][$id], $a[$key1]);
		}
	}
	return $info;
}

function fetchInfo($db, $tbl, $orderBy) {
	$info = array();
	$info['tbl'] = $tbl;
	$info['orderBy'] = $orderBy;
	$a = tableRows($db, $tbl, $orderBy);
	if (!empty($a)) $info['data'] = $a;
	$a = tableReference($db, $tbl);
	if (!empty($a)) $info['ref'] = $a;
	$a = tableSecondary($db, $tbl);
	if (!empty($a)) $info['secondary'] = $a;
	return $info;
}

if (empty($_GET['tbl'])) {exit(mkMsg(false, 'No tbl parameter supplied'));}

require_once 'php/DB1.php';

$tbl = $_GET['tbl'];
if (!$db->tableExists($tbl)) {exit(mkMsg(false, "Table, $tbl, does not exist"));}

if (empty($_GET['orderby'])) {
	$orderBy = '';
} else {
	$cols = $db->tableColumns($tbl);
	$a = explode(',', $_GET['orderby']);
	foreach ($a as $key) {
		if (!in_array(trim(strtolower($key)), $cols)) {
			exit(mkMsg(false, "Column, $key, unknown"));
		}
	}
	$orderBy = " ORDER BY " . implode(",", $a);
}

$db->listen(strtolower($tbl) . "_updated");

$info = fetchInfo($db, $tbl, $orderBy);
$info['info'] = tableInfo($db, $tbl);

while (True) { # Wait forever
	echo "data: " . json_encode($info) . "\n\n";
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	// Connections time out at ~60 seconds, so send a burp every ~55 seconds
	$notifications = $db->notifications(55000); 
	if ($notifications == false) { // no notifications
		$info = ['burp' => 0];
	} else { // notifications
		$info = fetchInfo($db, $tbl, $orderBy);
	}
}
?>
