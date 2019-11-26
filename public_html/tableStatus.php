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

function tableRows($db, $name, $orderBy, $where, $args) {
	$sql = "SELECT * FROM " . $name;
	if ($where != Null) $sql .= ' WHERE ' . $where;
	if ($orderBy != NULL) $sql .= $orderBy;
	$sql .= ";";
	return $db->loadRows($sql, $args);
}

function tablePgmStn($db, $where, $args) {
	$sql = "SELECT"
		. " pgmstn.id,pgmstn.program,pgmstn.station,pgmstn.mode,"
		. "pgmstn.runtime,pgmstn.priority"
		. " FROM pgmStn"
		. " INNER JOIN station ON pgmstn.station=station.id"
		. " INNER JOIN program ON pgmstn.program=program.id";
	if ($where != Null) $sql .= ' WHERE ' . $where;
	if ($orderBy != Null) $sql .= " ORDER BY station.name,program.name";
	$sql .= ";";

	return $db->loadRows($sql, $args);
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

function tableData($db, $tbl, $orderBy, $where, $args) {
	return $tbl == 'pgmStn'
		? tablePgmStn($db, $where, $args)
		: tableRows($db, $tbl, $orderBy, $where, $args);
}


function fetchInfo($db, $tbl, $orderBy, $where, $args) {
	$info = array();
	$info['tbl'] = $tbl;
	$info['orderBy'] = $orderBy;
	$a = tableData($db, $tbl, $orderBy, $where, $args);
	if (!empty($a)) $info['data'] = $a;
	$a = tableReference($db, $tbl);
	if (!empty($a)) $info['ref'] = $a;
	$a = tableSecondary($db, $tbl);
	if (!empty($a)) $info['secondary'] = $a;
	return $info;
}

function fetchRow($db, $tbl, $action, $id) { // Fetch a single row
	if ($action == 'DELETE') return ['action' => $action, 'id' => $id];
	$info = fetchInfo($db, $tbl, Null, "id=?", [$id]);
	$info['action'] = $action;
	$info['id'] = $id;
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

$db->listen(strtolower($tbl) . "_update");

$info = fetchInfo($db, $tbl, $orderBy, Null, []);
$info['info'] = tableInfo($db, $tbl);

while (True) { # Wait forever
	echo "data: " . json_encode($info) . "\n\n";
	if (ob_get_length()) {ob_flush();} // Flush output buffer
	flush();
	// Connections time out at ~60 seconds, so send a burp every ~55 seconds
	$notifications = $db->notifications(55000);
	if ($notifications == false) { // no notifications
		$info = ['burp' => 0];
		continue;
	} // if notifications
	$items = explode(' ', $notifications['payload']);
	if (count($items) != 3) { // Invalid notification
		$info = ['burp' => 0];
		continue;
	} // if
	$action = $items[1];
	$id = $items[2];
	$info = fetchRow($db, $tbl, $action, $id);
}
?>
