<?php

function csrfStartSession(): void {
	if (session_status() === PHP_SESSION_ACTIVE) return;

	$options = [
		'cookie_httponly' => true,
		'cookie_samesite' => 'Strict',
		'cookie_secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
		'use_strict_mode' => true,
	];
	if (session_start($options)) return;
	// The browser's session file exists but cannot be read, e.g. one written
	// by the previous php-fpm user after the pool moved to its own user (see
	// webserver/README.md). Start a new session rather than none at all.
	$id = session_create_id();
	if ($id !== false) session_id($id);
	session_start($options);
}

function csrfToken(): string {
	csrfStartSession();
	if (empty($_SESSION['csrf_token'])) {
		$_SESSION['csrf_token'] = bin2hex(random_bytes(32));
	}
	return $_SESSION['csrf_token'];
}

function csrfRequireValidPost(): void {
	if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
		http_response_code(405);
		header('Allow: POST');
		header('Content-Type: application/json');
		exit(json_encode(['success' => false, 'message' => 'POST required']));
	}

	csrfStartSession();
	$expected = $_SESSION['csrf_token'] ?? '';
	$provided = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? ($_POST['_csrf'] ?? '');
	if (!is_string($expected) || !is_string($provided)
			|| $expected === '' || !hash_equals($expected, $provided)) {
		http_response_code(403);
		header('Content-Type: application/json');
		exit(json_encode(['success' => false, 'message' => 'Invalid CSRF token']));
	}
	session_write_close();
}
