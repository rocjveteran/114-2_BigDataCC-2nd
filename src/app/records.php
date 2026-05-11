<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

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
$count = count($rows);
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>我的值勤紀錄 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php page_header(
      '我的值勤紀錄',
      '篩選日期區間查看您的歷次值勤。預設顯示本月。',
      'MY RECORDS · 個人紀錄'
    ); ?>

    <div class="card">
      <form method="get" class="filter-bar">
        <div>
          <label>開始日期</label>
          <input type="date" name="from" value="<?= h($from) ?>">
        </div>
        <div>
          <label>結束日期</label>
          <input type="date" name="to" value="<?= h($to) ?>">
        </div>
        <div class="filter-actions">
          <button class="btn primary" type="submit"><?= icon_svg('check') ?>查詢</button>
        </div>
      </form>

      <div class="card-head" style="border:0;padding:0;margin:0 0 8px;">
        <h2>勤務明細</h2>
        <span class="meta">共 <?= (int)$count ?> 筆</span>
      </div>

      <?php if ($count === 0): ?>
        <p class="muted" style="padding:20px 0;">此區間沒有任何值勤紀錄。</p>
      <?php else: ?>
      <table>
        <tr><th>日期</th><th>開始</th><th>結束</th><th>狀態</th></tr>
        <?php foreach($rows as $x):
          $st = $x['status'] ?? '';
          $label = $st;
          $type = 'off';
          if ($st === 'open') { $label = '值勤中'; $type = 'warn'; }
          if ($st === 'done') { $label = '已結束'; $type = 'ok'; }
        ?>
          <tr>
            <td><strong><?= h($x['work_date']) ?></strong></td>
            <td><?= h($x['check_in'] ?? '—') ?></td>
            <td><?= h($x['check_out'] ?? '—') ?></td>
            <td><?= badge($label ?: '無資料', $type) ?></td>
          </tr>
        <?php endforeach; ?>
      </table>
      <?php endif; ?>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
