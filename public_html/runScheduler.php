<?php
// form submission from index.php

require_once 'php/DB1.php';

if ($db->query("SELECT scheduler_notify('Web action');", []))
	exit($db->mkMsg(true, "Ran scheduler"));

echo $db->dbMsg("Failed to run scheduler");
?>
