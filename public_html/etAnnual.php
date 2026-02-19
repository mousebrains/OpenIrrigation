<?php
// Return day-of-year annual ET statistics from ETannual

require_once 'php/DB1.php';

if (empty($_POST['codigo'])) {
	echo json_encode(['success' => false, 'message' => 'No codigo supplied']);
	exit;
}

$sql = "SELECT doy, value, stddev FROM ETannual"
	. " WHERE code = ? ORDER BY doy;";
$rows = $db->loadRowsNum($sql, [$_POST['codigo']]);
echo json_encode($rows);
?>
