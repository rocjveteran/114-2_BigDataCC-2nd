<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

session_start();

// 已登入就直接進系統（避免登入中還看到登入頁）
if (isset($_SESSION['user_id'])) {
  header("Location: punch.php");
  exit;
}

require 'db.php';
require 'ui.php';

$error = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $username = trim($_POST['username'] ?? '');
  $password = $_POST['password'] ?? '';

  $stmt = $pdo->prepare("SELECT user_id, full_name, role, is_active, password_hash FROM users WHERE username=? LIMIT 1");
  $stmt->execute([$username]);
  $u = $stmt->fetch();

  if (!$u || !(int)$u['is_active'] || !password_verify($password, $u['password_hash'])) {
    $error = "帳號或密碼錯誤 / 帳號未啟用";
  } else {
    session_regenerate_id(true);
    $_SESSION['user_id'] = (int)$u['user_id'];
    $_SESSION['full_name'] = $u['full_name'];
    $_SESSION['role'] = $u['role'];
    header("Location: punch.php");
    exit;
  }
}
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>登入</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <?php nav_top('登入'); ?>

  <div class="wrap" style="max-width:520px;">
    <div class="card">
      <h1 class="h1">人員登入</h1>
      <div class="muted">請輸入帳號與密碼</div>

      <?php if ($error): ?>
        <p class="msg err" style="margin-top:10px;"><?= h($error) ?></p>
      <?php endif; ?>

      <form method="post" style="margin-top:10px;">
        <label>帳號</label>
        <input name="username" autocomplete="username" required placeholder="請輸入帳號">

        <label>密碼</label>
        <input name="password" type="password" autocomplete="current-password" required placeholder="請輸入密碼">

        <div style="margin-top:12px;">
          <button class="btn primary" type="submit"><?= icon_svg('login') ?>登入</button>
        </div>

        <div class="muted" style="margin-top:10px;">
          
        </div>
      </form>
    </div>
  </div>
</body>
</html>
