<?php
require_once __DIR__ . '/CSRF.php';

define('OI_CSRF_TOKEN', csrfToken());
session_write_close();
define('OI_ASSET_VERSION', '10');
