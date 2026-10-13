<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');
echo "retry: 10000\n\n";

function mkMsg(bool $q, string $msg): string {
	return "data: " .  json_encode(["success" => $q, "message" => $msg]) . "\n\n";
}

/** @return array<int, array<string, mixed>> */
function tableInfo(DB $db, string $name): array {
	$sql = 'SELECT * FROM tableInfo WHERE tbl=? ORDER BY displayOrder;';
	return $db->loadRows($sql, [$name]);
}

// What the editor is sent of each row: its id, qHide (rows the editor
// hides) and tableInfo's columns, but never a password column's value.
function selectColumns(DB $db, string $tbl): string {
	$a = ['id'];
	if ($db->hasColumn($tbl, 'qhide')) $a[] = 'qhide';
	foreach ($db->tableColumns($tbl) as $col => $type) {
		if ($type !== 'password') $a[] = $db->quoteIdent($col);
	}
	return implode(',', array_unique($a));
}

/** @param array<mixed> $args
 * @return array<int, array<string, mixed>> */
function tableRows(DB $db, string $name, ?string $orderBy, ?string $where, array $args): array {
	$sql = "SELECT " . selectColumns($db, $name) . " FROM " . $db->quoteIdent($name);
	if ($where !== null) $sql .= ' WHERE ' . $where;
	if ($orderBy !== null) $sql .= $orderBy;
	$sql .= ";";
	return $db->loadRows($sql, $args);
}

/** @param array<mixed> $args
 * @return array<int, array<string, mixed>> */
function tablePgmStn(DB $db, ?string $where, array $args): array {
	$sql = "SELECT"
		. " pgmstn.id,pgmstn.program,pgmstn.station,pgmstn.mode,"
		. "pgmstn.runtime,pgmstn.priority"
		. " FROM pgmStn"
		. " INNER JOIN station ON pgmstn.station=station.id"
		. " INNER JOIN program ON pgmstn.program=program.id";
	if ($where !== null) $sql .= ' WHERE ' . $where;
	$sql .= " ORDER BY station.name,program.name;";

	return $db->loadRows($sql, $args);
}

/** @return array<string, array<int, array<string, mixed>>> */
function tableReference(DB $db, string $name): array {
	$sql = "SELECT col,refTable,refKey,refLabel,refCriteria,refOrderBy"
		. " FROM tableInfo"
		. " WHERE tbl=? AND refTable IS NOT NULL;";
	$info = [];
	foreach ($db->loadRows($sql, [$name]) as $row) {
		$tbl = $db->quoteIdent($row['reftable']);
		$col = $row['col'];
		$sql = "SELECT " . $db->quoteIdent($row['refkey']) . " AS id,"
			. $db->quoteIdent($row['reflabel']) . " AS name"
			. " FROM " . $tbl;
		if ($row['refcriteria'] !== null && DB::isValidCriteria($row['refcriteria']))
			$sql .= " WHERE " . $row['refcriteria'];
		if ($row['reforderby'] !== null && DB::isValidOrderBy($row['reforderby']))
			$sql .= " ORDER BY " . $row['reforderby'];
		$sql .= ";";
		$info[$col] = $db->loadRows($sql, []);
	}
	return $info;
}

/** @return array<string, array<int|string, array<int, mixed>>> */
function tableSecondary(DB $db, string $name): array {
	$sql = "SELECT col,secondaryKey AS key0,secondaryValue AS key1 FROM tableInfo"
		. " WHERE tbl=? AND secondaryKey IS NOT NULL;";
	$info = [];
	foreach ($db->loadRows($sql, [$name]) as $row) {
		$col = $db->quoteIdent($row['col']);
		$key0 = $db->quoteIdent($row['key0']);
		$key1 = $db->quoteIdent($row['key1']);
		$sql = "SELECT $key0,$key1 FROM $col;";
		$info[$col] = [];
		foreach ($db->loadRows($sql, []) as $a) {
			$id = $a[$key0];
			if (!array_key_exists($id, $info[$col])) $info[$col][$id] = [];
			$info[$col][$id][] = $a[$key1];
		}
	}
	return $info;
}

/** @param array<mixed> $args
 * @return array<int, array<string, mixed>> */
function tableData(DB $db, string $tbl, ?string $orderBy, ?string $where, array $args): array {
	return $tbl == 'pgmStn'
		? tablePgmStn($db, $where, $args)
		: tableRows($db, $tbl, $orderBy, $where, $args);
}


/** @param array<mixed> $args
 * @return array<string, mixed> */
function fetchInfo(DB $db, string $tbl, ?string $orderBy, ?string $where, array $args): array {
	$info = [];
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

/** @return array<string, mixed> */
function fetchRow(DB $db, string $tbl, string $action, string $id): array { // Fetch a single row
	if ($action == 'DELETE') return ['action' => $action, 'id' => $id];
	$info = fetchInfo($db, $tbl, Null, "$tbl.id=?", [$id]);
	$info['action'] = $action;
	$info['id'] = $id;
	return $info;
}

$tblParam = $_GET['tbl'] ?? null;
if (!is_string($tblParam) || $tblParam === '') {exit(mkMsg(false, 'No tbl parameter supplied'));}

require_once 'php/DB1.php';
$db = DB::getInstance();

// A database error is transient: send it as an error frame and end the
// stream, so EventSource reconnects. A message frame makes the editor stop.
function dbError(): never {
	echo "data: " . json_encode(["error" => "Database error"]) . "\n\n";
	exit;
}

try {
	$tbl = $db->tableName($tblParam);
	if ($tbl === null) {exit(mkMsg(false, "Table, $tblParam, is not editable"));}

	$orderBy = null;
	if (isset($_GET['orderby']) && $_GET['orderby'] !== '') {
		if (!is_string($_GET['orderby'])) {exit(mkMsg(false, 'Invalid orderby'));}
		$cols = $db->tableColumns($tbl);
		$a = [];
		foreach (explode(',', $_GET['orderby']) as $key) {
			$col = trim(strtolower($key)); // Validate, then use the validated form
			if (!array_key_exists($col, $cols) || $cols[$col] === 'password') {
				exit(mkMsg(false, "Column, $key, unknown"));
			}
			$a[] = $db->quoteIdent($col);
		}
		$orderBy = " ORDER BY " . implode(",", $a);
	}

	$db->listen(strtolower($tbl) . "_update");

	$info = fetchInfo($db, $tbl, $orderBy, Null, []);
	$info['info'] = tableInfo($db, $tbl);
} catch (PDOException $e) {
	dbError();
}

try {
	while (!connection_aborted()) { # Wait until client disconnects
		echo "data: " . json_encode($info) . "\n\n";
		if (ob_get_length()) {ob_flush();} // Flush output buffer
		flush();
		// 25-second burp keeps iOS WiFi power-save from dropping idle connection
		$notifications = $db->notifications(25000);
		$payload = $notifications === false ? null : ($notifications['payload'] ?? null);
		$items = is_string($payload) ? explode(' ', $payload) : [];
		if (count($items) != 3) { // No or invalid notification
			$info = ['burp' => 0];
			continue;
		} // if
		$action = $items[1];
		$id = $items[2];
		$info = fetchRow($db, $tbl, $action, $id);
	}
} catch (PDOException $e) {
	dbError(); // Dead DB connection would busy-loop; let EventSource reconnect
}
