<?php
// The session's CSRF token, starting a new session if the old one has
// expired, so an open page can retry a POST that failed with "Invalid CSRF
// token" (OI_refreshCSRF in js/irrigation.js). Same-origin only: the
// session cookie is SameSite=Strict and the reply is JSON, not script.
require_once 'php/CSRF.php';

header('Content-Type: application/json');
header('Cache-Control: no-store');
$token = csrfToken();
session_write_close();
echo json_encode(['token' => $token]);
