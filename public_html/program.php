<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Program editor</title>
<style> tbody tr:nth-of-type(odd) {background-color:#eee;} </style>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webPage.php';

session_start();
$pb = new PageBuilder('program', $parDB, True);
if (!empty($_POST)) $pb->postUp($_POST);
$pb->mkPage();
?>
</body>
</html>
