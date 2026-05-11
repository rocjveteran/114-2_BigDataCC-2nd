<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

$stmt = $pdo->query("SELECT user_id, username, full_name, role, is_active, created_at FROM users ORDER BY user_id DESC LIMIT 200");
$rows = $stmt->fetchAll();
$count = count($rows);
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>人員名單 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php page_header(
      '人員名單',
      '查看所有人員的帳號狀態。員工僅可查看，不可進行管理操作。',
      'DIRECTORY · 名冊'
    ); ?>

    <div class="card">
      <div class="card-head" style="border:0;padding:0;margin:0 0 8px;">
        <h2>所有人員</h2>
        <span class="meta">共 <?= (int)$count ?> 人</span>
      </div>
      <table>
        <tr><th>ID</th><th>帳號</th><th>姓名</th><th>角色</th><th>狀態</th><th>建立時間</th></tr>
        <?php foreach($rows as $u): ?>
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
