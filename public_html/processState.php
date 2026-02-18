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
<title>Process Status</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
?>
<div class='table-wrap'>
<table>
<thead><tr><th>Item</th><th>Date</th><th>Message</th></tr></thead>
<tbody id='messages'></tbody>
<tfoot><tr><th>Item</th><th>Date</th><th>Message</th></tr></tfoot>
</table>
</div>
<script defer src="js/processState.js?v=<?php echo OI_ASSET_VERSION; ?>"></script>
</body>
</html>
