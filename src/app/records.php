<?php
require 'auth.php';
require 'db.php';

$userId = (int)$_SESSION['user_id'];
$from = $_GET['from'] ?? date('Y-m-01');
$to   = $_GET['to'] ?? date('Y-m-d');

$stmt = $pdo->prepare(
  "SELECT work_date, check_in, check_out, status
   FROM attendance
   WHERE user_id=? AND work_date BETWEEN ? AND ?
   ORDER BY work_date DESC"
);
$stmt->execute([$userId, $from, $to]);
$rows = $stmt->fetchAll();
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>我的值勤紀錄</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <?php require 'ui.php'; nav_top('我的值勤紀錄'); ?>
  <div class="wrap" style="max-width:980px;">
    <div class="card">
      <form method="get">
        <div class="row">
          <div>
            <label>From</label>
            <input type="date" name="from" value="<?= h($from) ?>">
          </div>
          <div>
            <label>To</label>
            <input type="date" name="to" value="<?= h($to) ?>">
          </div>
        </div>
        <div style="margin-top:12px;">
          <button class="btn primary" type="submit">查詢</button>
        </div>
      </form>

      <table>
        <tr><th>日期</th><th>值勤開始</th><th>值勤結束</th><th>狀態</th></tr>
        <?php foreach($rows as $x): ?>
          <?php
            $st = $x['status'] ?? '';
            $label = $st;
            $type = 'off';
            if ($st === 'open') { $label = '值勤開始中'; $type = 'warn'; }
            if ($st === 'done') { $label = '已值勤結束'; $type = 'ok'; }
          ?>
          <tr>
            <td><?= h($x['work_date']) ?></td>
            <td><?= h($x['check_in'] ?? '-') ?></td>
            <td><?= h($x['check_out'] ?? '-') ?></td>
            <td><?= badge($label ?: 'none', $type) ?></td>
          </tr>
        <?php endforeach; ?>
      </table>
    </div>
  </div>
</body>
</html>
