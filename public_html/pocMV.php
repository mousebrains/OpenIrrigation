<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>POC Master Valve editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/mkPage.php';

$pb = new PageBuilder('pocMV', $db, ['orderBy'=>'name', 'qTable'=>False]);
if (!empty($_POST)) $pb->postUp($_POST);
$pb->mkPage();
?>
</body>
</html>
