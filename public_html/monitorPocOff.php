<?php
// Turn POCs on/off, clear all pending actions, or shut everything off

require_once 'php/DB1.php';
$db = DB::getInstance();

if (empty($_POST['poc'])) exit($db->mkMsg(false, 'No POC supplied'));

$poc = $_POST['poc'];
$dt = 60;

if ($db->query("SELECT poc_off(?,?)", [$poc, $dt]))
	exit($db->mkMsg(true, "Turned POC($poc) off for $dt minutes"));
echo $db->dbMsg("Failed to turn off POC($poc) for $dt minutes");
?>
