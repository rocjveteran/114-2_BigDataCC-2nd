<?php
require 'db.php';
require 'ui.php';   // session_start + hardening + csrf

if (isset($_SESSION['user_id'])) {
  header("Location: dashboard.php");
  exit;
}

$error = null;
$locked_until = null;

// ── Login throttle: 5 attempts per 15 min per session ──
$MAX_ATTEMPTS  = 5;
$LOCK_SECONDS  = 900;
$now = time();
$fail_count = (int)($_SESSION['login_fail_count']  ?? 0);
$fail_first = (int)($_SESSION['login_fail_first']  ?? 0);
$fail_last  = (int)($_SESSION['login_fail_last']   ?? 0);

// Reset counter if last failure older than the lockout window
if ($fail_count > 0 && ($now - $fail_last) > $LOCK_SECONDS) {
  $_SESSION['login_fail_count'] = 0;
  $_SESSION['login_fail_first'] = 0;
  $_SESSION['login_fail_last']  = 0;
  $fail_count = 0;
}

$is_locked = false;
if ($fail_count >= $MAX_ATTEMPTS && ($now - $fail_last) <= $LOCK_SECONDS) {
  $is_locked   = true;
  $locked_until = $fail_last + $LOCK_SECONDS;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  csrf_require();

  if ($is_locked) {
    $remain = max(1, (int)ceil(($locked_until - $now) / 60));
    $error = "登入嘗試過多，請於 {$remain} 分鐘後再試。";
  } else {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    $stmt = $pdo->prepare("SELECT user_id, full_name, role, is_active, password_hash FROM users WHERE username=? LIMIT 1");
    $stmt->execute([$username]);
    $u = $stmt->fetch();

    if (!$u || !(int)$u['is_active'] || !password_verify($password, $u['password_hash'])) {
      // Count failure
      $_SESSION['login_fail_count'] = $fail_count + 1;
      if (!$fail_first) $_SESSION['login_fail_first'] = $now;
      $_SESSION['login_fail_last'] = $now;
      $remaining = $MAX_ATTEMPTS - $_SESSION['login_fail_count'];
      $error = "帳號或密碼錯誤 / 帳號未啟用" . ($remaining > 0 ? "（剩 {$remaining} 次）" : "");
      // Trigger lock if reached
      if ($_SESSION['login_fail_count'] >= $MAX_ATTEMPTS) {
        $is_locked = true;
        $locked_until = $now + $LOCK_SECONDS;
        $error = "登入嘗試過多，請於 15 分鐘後再試。";
      }
    } else {
      // Success — reset counter and regenerate session
      $_SESSION['login_fail_count'] = 0;
      $_SESSION['login_fail_first'] = 0;
      $_SESSION['login_fail_last']  = 0;
      session_regenerate_id(true);
      $_SESSION['user_id']   = (int)$u['user_id'];
      $_SESSION['full_name'] = $u['full_name'];
      $_SESSION['role']      = $u['role'];
      header("Location: dashboard.php");
      exit;
    }
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

    <svg class="login-particles" viewBox="0 0 800 80" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <?php
        // 散落粒子波（Spyder-inspired）— 固定 seed 確保重整時位置一致，不會跳動
        mt_srand(0x5A4B);
        for ($i = 0; $i < 140; $i++) {
          $x = mt_rand(0, 800);
          // 主波形 baseline + 隨機 jitter，形成「粒子組成的波帶」
          $wave_y = 40 + 14 * sin($x * 0.022);
          $jitter = mt_rand(-26, 26);
          $y = max(3, min(77, (int)($wave_y + $jitter)));
          $r  = mt_rand(7, 22) / 10;       // 0.7 ~ 2.2 px
          $op = mt_rand(14, 50) / 100;     // 0.14 ~ 0.50
          echo sprintf('<circle cx="%d" cy="%d" r="%.1f" fill="var(--accent)" opacity="%.2f"/>', $x, $y, $r, $op);
        }
      ?>
    </svg>

    <div class="card">
      <?php if ($error): ?>
        <p class="msg err"><?= h($error) ?></p>
      <?php endif; ?>

      <form method="post" autocomplete="on">
        <?= csrf_input() ?>
        <label>帳號</label>
        <input name="username" autocomplete="username" required placeholder="例如：admin" <?= $is_locked?'disabled':'' ?>>

        <label>密碼</label>
        <input name="password" type="password" autocomplete="current-password" required placeholder="輸入您的密碼" <?= $is_locked?'disabled':'' ?>>

        <div class="form-actions">
          <button class="btn primary" type="submit" style="flex:1;" <?= $is_locked?'disabled':'' ?>><?= icon_svg('login') ?>登入</button>
        </div>
      </form>

      <div class="login-scope">
        <span class="scope-dot"></span>
        勤務打卡 · 請假審核 · 艦上人員配置 · 海象連動 · 統計分析
      </div>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
