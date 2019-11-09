<?php
// form submission from index.php

require_once 'php/DB1.php';

if ($db->query("SELECT scheduler_notify('Web action');", []))
	exit(json_encode(['success' => true, 'message' => 'Ran scheduler']));

echo json_encode(['success' => false, 'message' => 'Failed to run scheduler, ' . $db->getError()]);
?>
