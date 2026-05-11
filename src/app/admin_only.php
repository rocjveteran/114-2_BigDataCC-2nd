<?php
// admin_only.php - require boss/admin
require 'auth.php';

$role = $_SESSION['role'] ?? '';
if (!in_array($role, ['boss','admin'], true)) {
  http_response_code(403);
  echo "<div style='font-family:system-ui;padding:20px'>你沒有權限</div>";
  exit;
}
