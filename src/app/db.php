<?php
// db.php - PDO connection (reads from environment variables for Docker)

// ── Error reporting guard ──
// Default: production-safe (no stack traces in HTTP response).
// Set APP_ENV=dev (e.g. in docker/.env) to re-enable verbose errors during development.
if (getenv('APP_ENV') === 'dev') {
  ini_set('display_errors', '1');
  ini_set('display_startup_errors', '1');
  error_reporting(E_ALL);
} else {
  ini_set('display_errors', '0');
  ini_set('display_startup_errors', '0');
  ini_set('log_errors', '1');
  error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED);
}

$host    = getenv('DB_HOST') ?: 'localhost';
$db      = getenv('DB_NAME') ?: 'maritime_duty';
$user    = getenv('DB_USER') ?: 'root';
$pass    = getenv('DB_PASS') ?: '';
$charset = 'utf8mb4';

$dsn = "mysql:host={$host};dbname={$db};charset={$charset}";
$options = [
  PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
  PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
  PDO::ATTR_EMULATE_PREPARES   => false,
];

try {
  $pdo = new PDO($dsn, $user, $pass, $options);
} catch (PDOException $e) {
  http_response_code(500);
  echo "DB connection failed. Please check db.php settings.";
  exit;
}
