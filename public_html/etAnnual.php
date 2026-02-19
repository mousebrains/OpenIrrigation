<?php
// Return day-of-year annual ET statistics from ETannual

require_once 'php/DB1.php';

if (empty($_POST['codigo'])) {
	echo json_encode(['success' => false, 'message' => 'No codigo supplied']);
	exit;
}

$codigo = $_POST['codigo'];

$sql = "SELECT doy, q10, value, q90 FROM ETannual"
	. " WHERE code = ? ORDER BY doy;";
$annual = $db->loadRowsNum($sql, [$codigo]);

$sql = "SELECT EXTRACT('DOY' FROM t)::integer, value FROM ET"
	. " WHERE code = ? AND t >= DATE_TRUNC('year', CURRENT_DATE) ORDER BY t;";
$ytd = $db->loadRowsNum($sql, [$codigo]);

$sql = "SELECT EXTRACT('DOY' FROM t)::integer, value FROM ET"
	. " WHERE code = ? AND t >= DATE_TRUNC('year', CURRENT_DATE) - INTERVAL '1 year'"
	. " AND t < DATE_TRUNC('year', CURRENT_DATE)"
	. " AND EXTRACT('DOY' FROM t) >= EXTRACT('DOY' FROM CURRENT_DATE)"
	. " ORDER BY t;";
$prev = $db->loadRowsNum($sql, [$codigo]);

echo json_encode(['annual' => $annual, 'ytd' => $ytd, 'prev' => $prev]);
?>
