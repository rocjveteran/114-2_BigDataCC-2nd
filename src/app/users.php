<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

$stmt = $pdo->query("SELECT user_id, username, full_name, role, is_active, created_at FROM users ORDER BY user_id DESC LIMIT 200");
$rows = $stmt->fetchAll();

function role_name($r){
  if ($r==='boss') return 'boss';
  if ($r==='admin') return 'admin';
  return 'employee';
}
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>人員名單</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <?php nav_top('人員名單'); ?>
  <div class="wrap">
    <div class="card">
      <div class="muted">員工僅可查看，不可操作。</div>
      <table>
        <tr><th>ID</th><th>帳號</th><th>姓名</th><th>角色</th><th>狀態</th><th>建立時間</th></tr>
        <?php foreach($rows as $u): ?>
          <tr>
            <td><?= h($u['user_id']) ?></td>
            <td><?= h($u['username']) ?></td>
            <td><?= h($u['full_name']) ?></td>
            <td><?= h(role_name($u['role'])) ?></td>
            <td><?= ((int)$u['is_active']===1) ? badge('啟用','ok') : badge('停用','off') ?></td>
            <td><?= h($u['created_at']) ?></td>
          </tr>
        <?php endforeach; ?>
      </table>
    </div>
  </div>
</body>
</html>
