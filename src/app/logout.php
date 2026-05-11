<?php
session_start();

// 1) 清空 session 內容
$_SESSION = [];

// 2) 刪除 session cookie
if (ini_get("session.use_cookies")) {
  $p = session_get_cookie_params();
  setcookie(session_name(), '', time() - 42000, $p['path'], $p['domain'], $p['secure'], $p['httponly']);
}

// 3) 銷毀 session
session_destroy();

// 4) 回登入頁
header("Location: login.php");
exit;
