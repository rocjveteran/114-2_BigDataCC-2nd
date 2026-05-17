<?php
// csrf.php — Lightweight per-session CSRF token system.
// Usage (description only, do not paste sample with literal short-tags into this PHP source):
//   1) require 'csrf.php'
//   2) emit csrf_input() inside every POST form
//   3) call csrf_require() at the top of any POST handler
if (session_status() === PHP_SESSION_NONE) session_start();

function csrf_token(): string {
  if (empty($_SESSION['_csrf'])) {
    $_SESSION['_csrf'] = bin2hex(random_bytes(32));
  }
  return $_SESSION['_csrf'];
}

function csrf_input(): string {
  return '<input type="hidden" name="_csrf" value="'.htmlspecialchars(csrf_token(), ENT_QUOTES, 'UTF-8').'">';
}

function csrf_verify(?string $token = null): bool {
  $token = $token ?? ($_POST['_csrf'] ?? '');
  $expected = $_SESSION['_csrf'] ?? '';
  return $token !== '' && $expected !== '' && hash_equals($expected, $token);
}

function csrf_require(): void {
  if (!csrf_verify()) {
    http_response_code(403);
    echo '<!doctype html><meta charset="utf-8"><title>403</title><body style="font-family:system-ui;padding:40px;color:#333"><h1>403 — CSRF token 驗證失敗</h1><p>請從正常頁面操作，或重新整理後再試一次。</p><p><a href="dashboard.php">返回首頁</a></p></body>';
    exit;
  }
}
