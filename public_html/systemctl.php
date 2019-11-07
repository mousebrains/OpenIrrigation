<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='icon' href='/favicon.png' sizes="32x32">
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<script src="js/irrigation.js"></script>
<title>System status</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
echo "<pre>\n";
$lastLine = system("/bin/systemctl --full --no-pager status OITDI OISched OIAgriMet", $retval);
echo "</pre>\n";
echo "<hr>\n";
echo "Return value: $retval\n";
?>
</body>
</html> 
