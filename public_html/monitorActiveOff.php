<?php
// Turn off an active valve from monitor.php

require_once 'php/DB1.php';

if (empty($_POST['id'])) exit($db->mkMsg(false, "No ID supplied."));

$id = $_POST['id'];

if ($db->query('SELECT manual_off(?);', [$id])) exit($db->mkMsg(true, "Turned Valve $id off"));
echo $db->dbMsg("Failed to turn valve($id) off");
?>
