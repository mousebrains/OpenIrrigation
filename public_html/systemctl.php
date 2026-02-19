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
<title>System status</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
echo "<pre>\n";
$output = shell_exec("/bin/systemctl --full --no-pager status OITDI OISched");
if ($output === null || $output === false) {
	echo "Error: unable to run systemctl\n";
} else {
	echo htmlspecialchars($output, ENT_QUOTES, 'UTF-8');
}
echo "</pre>\n";
echo "<hr>\n";
?>
</body>
</html>
