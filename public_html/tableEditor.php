<?php require_once 'php/version.php'; ?>
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='icon' href='/favicon.png' sizes="32x32">
<link rel='stylesheet' type='text/css' href='css/irrigation.css?v=<?php echo OI_ASSET_VERSION; ?>'>
<script defer src="js/jquery.min.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<script defer src="js/irrigation.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
<title>Parameter Editor</title>
</head>
<body>
<?php
$tblParam = $_GET['tbl'] ?? null;
if (!is_string($tblParam) || $tblParam === '') {exit("<h1>tbl parameter not supplied</h1>\n</body>\n</html>\n");}

require_once 'php/DB1.php';
$db = DB::getInstance();
try {
	$tbl = $db->tableName($tblParam);
} catch (PDOException $e) {
	exit("<h1>Database error</h1>\n</body>\n</html>\n");
}
if ($tbl === null) {exit("<h1>Table, " . htmlspecialchars($tblParam, ENT_QUOTES, 'UTF-8') . ", is not editable</h1>\n</body>\n</html>\n");}
echo '<div id="oi-config" data-table-name="' . htmlspecialchars($tbl, ENT_QUOTES, 'UTF-8') . '" hidden></div>';

require_once 'php/navBar.php';
?>
<div class='table-wrap'>
<table>
<thead></thead>
<tbody></tbody>
<tfoot></tfoot>
</table>
<form action='javascript:void(0);'>
<input type='button' value='Batch Update' id='batchUpdate'>
<input type='button' value='Cancel' id='batchCancel'>
</form>
</div>
<script defer src="js/tableEditor.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
</body>
</html>
