<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

session_start();

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
  <title>登入 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>

  <div class="wrap narrow" style="padding-top:48px;">
    <?php page_header('登入系統', '請以您的帳號與密碼進入。如忘記密碼，請聯絡管理者。', 'ACCESS · 存取'); ?>

    <div class="card">
      <?php if ($error): ?>
        <p class="msg err"><?= h($error) ?></p>
      <?php endif; ?>

      <form method="post" autocomplete="on">
        <label>帳號</label>
        <input name="username" autocomplete="username" required placeholder="例如：admin">

        <label>密碼</label>
        <input name="password" type="password" autocomplete="current-password" required placeholder="輸入您的密碼">

        <div class="form-actions">
          <button class="btn primary" type="submit" style="flex:1;"><?= icon_svg('login') ?>登入</button>
        </div>
      </form>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
