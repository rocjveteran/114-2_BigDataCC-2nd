<?php
require_once __DIR__ . '/ui.php'; // starts hardened session + loads csrf

// Only accept POST with valid CSRF, to prevent forced logout via <img src>
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  // Fallback: render a tiny confirm form so users typing /logout.php in URL still work.
  ?><!doctype html>
  <html lang="zh-TW"><head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>登出 · 海事勤務</title><?php style_link(); ?>
  </head><body>
    <?php nav_top(); ?>
    <div class="wrap narrow" style="padding-top:48px;">
      <?php page_header('登出', '請確認要登出系統。', 'ACCESS · 存取'); ?>
      <div class="card">
        <form method="post">
          <?= csrf_input() ?>
          <div class="form-actions">
            <button class="btn primary" type="submit"><?= icon_svg('logout') ?>確認登出</button>
            <a class="btn ghost" href="dashboard.php">取消</a>
          </div>
        </form>
      </div>
    </div>
    <?php page_footer(); ?>
  </body></html>
  <?php
  exit;
}

csrf_require();

// 1) Clear session payload
$_SESSION = [];

// 2) Delete session cookie
if (ini_get('session.use_cookies')) {
  $p = session_get_cookie_params();
  setcookie(session_name(), '', time() - 42000, $p['path'], $p['domain'], $p['secure'], $p['httponly']);
}

// 3) Destroy session
session_destroy();

// 4) Redirect to login (303 forces GET on redirect after POST)
header('Location: login.php', true, 303);
exit;
