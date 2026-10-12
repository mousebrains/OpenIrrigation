<?php
// form submission from index.php

require_once 'php/CSRF.php';
csrfRequireValidPost();
require_once 'php/DB1.php';
$db = DB::getInstance();

try {
	$db->query("SELECT scheduler_notify('Web action');", []);
} catch (PDOException $e) {
	exit($db->errMsg($e, "Failed to run scheduler"));
}
echo $db->mkMsg(true, "Ran scheduler");
