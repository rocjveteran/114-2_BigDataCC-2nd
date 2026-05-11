<?php
require 'admin_only.php';
require 'db.php';
require_once 'ui.php';

$msg = null;
$err = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $username = trim($_POST['username'] ?? '');
  $full_name = trim($_POST['full_name'] ?? '');
  $password = $_POST['password'] ?? '';
  $role = $_POST['role'] ?? 'employee';

  // permission: admin can create employees only
  if (!is_boss() && $role !== 'employee') {
    $err = '你沒有權限建立管理員';
  }

  $is_active = isset($_POST['is_active']) ? 1 : 0;

  if (!$err && ($username === '' || $full_name === '' || $password === '')) {
    $err = "請填寫 username / full_name / password";
  } else if (!in_array($role, ['employee','admin'], true)) {
    $err = "角色不合法";
  } else {
    try {
      $stmt = $pdo->prepare("SELECT user_id FROM users WHERE username=? LIMIT 1");
      $stmt->execute([$username]);
      if ($stmt->fetch()) {
        $err = "username 已存在";
      } else {
        $hash = password_hash($password, PASSWORD_DEFAULT);
        $ins = $pdo->prepare("INSERT INTO users(username, password_hash, full_name, role, is_active) VALUES(?,?,?,?,?)");
        $ins->execute([$username, $hash, $full_name, $role, $is_active]);
        $msg = "新增成功：" . $username;
      }
    } catch (Exception $e) {
      $err = "新增失敗（請重試）";
    }
  }
}

$stmt = $pdo->query("SELECT user_id, username, full_name, role, is_active, created_at FROM users ORDER BY user_id DESC LIMIT 20");
$users = $stmt->fetchAll();
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>帳號管理</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <?php require_once 'ui.php'; nav_top('帳號管理'); ?>
  <div class="wrap">
    <div class="card">
      <div class="toolbar">
        <div class="title"><h1>新增帳號</h1><div class="hint">建立後可在「帳號管理」修改/停用</div></div>
        <div class="actions">
          <a class="btn" href="admin_users.php"><?= icon_svg("users") ?>帳號管理</a>
          <a class="btn" href="admin_status.php"><?= icon_svg("list") ?>值勤總覽</a>
        </div>
      </div>
      <div class="muted">只有管理者可使用。新增後人員可直接登入。</div>

      <?php if($msg): ?><p class="msg ok" style="margin-top:12px;"><?= h($msg) ?></p><?php endif; ?>
      <?php if($err): ?><p class="msg err" style="margin-top:12px;"><?= h($err) ?></p><?php endif; ?>

      <form method="post" autocomplete="off" style="margin-top:10px;">
        <div class="row">
          <div>
            <label>username</label>
            <input name="username" required placeholder="請輸入帳號">
          </div>
          <div>
            <label>full_name</label>
            <input name="full_name" required placeholder="請輸入姓名">
          </div>
        </div>

        <div class="row">
          <div>
            <label>password</label>
            <input name="password" type="password" required placeholder="請輸入密碼">
          </div>
          <div>
            <label>role</label>
            <select name="role">
              <?php if(is_boss()): ?>
                <option value="employee" selected>employee</option>
                <option value="admin">admin</option>
              <?php else: ?>
                <option value="employee" selected>employee</option>
              <?php endif; ?>
            </select>
          </div>
        </div>

        <label style="display:flex;gap:10px;align-items:center;margin-top:10px;">
          <input type="checkbox" name="is_active" checked style="width:auto;">
          啟用帳號（is_active=1）
        </label>

        <div style="margin-top:12px;">
          <button class="btn okfill" type="submit"><?= icon_svg("plus") ?>建立帳號</button>
          <a class="btn" href="admin_status.php"><?= icon_svg("list") ?>值勤總覽</a>
        </div>
      </form>

      <div class="card" style="margin-top:12px;">
        <h2 class="h2">最近 20 筆帳號</h2>
        <table>
          <tr><th>ID</th><th>username</th><th>full_name</th><th>role</th><th>active</th><th>created_at</th></tr>
          <?php foreach($users as $u): ?>
            <tr>
              <td><?= h($u['user_id']) ?></td>
              <td><?= h($u['username']) ?></td>
              <td><?= h($u['full_name']) ?></td>
              <td><?= h($u['role']) ?></td>
              <td><?= h($u['is_active']) ?></td>
              <td><?= h($u['created_at']) ?></td>
            </tr>
          <?php endforeach; ?>
        </table>
      </div>
    </div>
  </div>
</body>
</html>