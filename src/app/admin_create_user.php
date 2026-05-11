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
  <title>新增帳號 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap mid">
    <?php
    $actions = '<a class="btn ghost" href="admin_users.php">'.icon_svg('users').'回帳號管理</a>';
    page_header(
      '新增帳號',
      '建立新使用者後，可直接登入系統。admin 僅能建立 employee；boss 可建立 admin。',
      'ADMIN · 管理',
      $actions
    );
    ?>

    <?php if($msg): ?><p class="msg ok"><?= h($msg) ?></p><?php endif; ?>
    <?php if($err): ?><p class="msg err"><?= h($err) ?></p><?php endif; ?>

    <div class="card">
      <form method="post" autocomplete="off">
        <div class="row">
          <div>
            <label>帳號 (username)</label>
            <input name="username" required placeholder="例如：j.chen">
          </div>
          <div>
            <label>姓名 (full_name)</label>
            <input name="full_name" required placeholder="例如：陳俊宏">
          </div>
        </div>

        <div class="row">
          <div>
            <label>初始密碼</label>
            <input name="password" type="password" required placeholder="至少 6 字元">
          </div>
          <div>
            <label>角色</label>
            <select name="role">
              <?php if(is_boss()): ?>
                <option value="employee" selected>employee（員工）</option>
                <option value="admin">admin（管理員）</option>
              <?php else: ?>
                <option value="employee" selected>employee（員工）</option>
              <?php endif; ?>
            </select>
          </div>
        </div>

        <label style="display:flex;gap:10px;align-items:center;margin-top:18px;text-transform:none;letter-spacing:0;font-size:14px;color:var(--text);">
          <input type="checkbox" name="is_active" checked style="width:auto;">
          建立後立即啟用帳號
        </label>

        <div class="form-actions">
          <button class="btn primary" type="submit"><?= icon_svg("plus") ?>建立帳號</button>
          <a class="btn ghost" href="admin_users.php">取消</a>
        </div>
      </form>
    </div>

    <div class="card">
      <div class="card-head" style="border:0;padding:0;margin:0 0 8px;">
        <h2>最近建立的帳號</h2>
        <span class="meta">最多 20 筆</span>
      </div>
      <table>
        <tr><th>ID</th><th>帳號</th><th>姓名</th><th>角色</th><th>啟用</th><th>建立時間</th></tr>
        <?php foreach($users as $u): ?>
          <tr>
            <td><?= h($u['user_id']) ?></td>
            <td><?= h($u['username']) ?></td>
            <td><?= h($u['full_name']) ?></td>
            <td><?= h(role_name($u['role'])) ?></td>
            <td><?= ((int)$u['is_active']===1) ? badge('啟用','ok') : badge('停用','off') ?></td>
            <td class="muted"><?= h($u['created_at']) ?></td>
          </tr>
        <?php endforeach; ?>
      </table>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
