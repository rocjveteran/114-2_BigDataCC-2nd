<?php
require 'auth.php';
require 'db.php';

date_default_timezone_set('Asia/Taipei');

$uid = (int)$_SESSION['user_id'];
$d   = date('Y-m-d');
$now = date('Y-m-d H:i:s');

$msg = null;

$stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
$stmt->execute([$uid, $d]);
$a = $stmt->fetch();

// leave check (approved)
$stmt = $pdo->prepare("SELECT leave_type FROM leaves WHERE user_id=? AND status='approved' AND date_from<=? AND date_to>=? LIMIT 1");
$stmt->execute([$uid, $d, $d]);
$lv = $stmt->fetchColumn();


if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $act = $_POST['act'] ?? '';

  $pdo->beginTransaction();
  try {
    $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? FOR UPDATE");
    $stmt->execute([$uid, $d]);
    $row = $stmt->fetch();

    if ($act === 'in') {
      if (!$row) {
        $ins = $pdo->prepare("INSERT INTO attendance(user_id, work_date, check_in, status) VALUES(?,?,?,'open')");
        $ins->execute([$uid, $d, $now]);
        $msg = "值勤開始值勤成功：{$now}";
      } else if (empty($row['check_in'])) {
        $upd = $pdo->prepare("UPDATE attendance SET check_in=?, status='open' WHERE att_id=?");
        $upd->execute([$now, (int)$row['att_id']]);
        $msg = "值勤開始值勤成功：{$now}";
      } else {
        $msg = "已值勤開始，不能重複值勤開始值勤。";
      }
    } elseif ($act === 'out') {
      if (!$row || empty($row['check_in'])) {
        $msg = "尚未值勤開始，不能值勤結束值勤。";
      } else if (!empty($row['check_out'])) {
        $msg = "已值勤結束，不能重複值勤結束值勤。";
      } else {
        $upd = $pdo->prepare("UPDATE attendance SET check_out=?, status='done' WHERE att_id=?");
        $upd->execute([$now, (int)$row['att_id']]);
        $msg = "值勤結束值勤成功：{$now}";
      }
    }

    $pdo->commit();
  } catch (Exception $e) {
    $pdo->rollBack();
    $msg = "值勤失敗（請重試）";
  }

  $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
  $stmt->execute([$uid, $d]);
  $a = $stmt->fetch();

// leave check (approved)
$stmt = $pdo->prepare("SELECT leave_type FROM leaves WHERE user_id=? AND status='approved' AND date_from<=? AND date_to>=? LIMIT 1");
$stmt->execute([$uid, $d, $d]);
$lv = $stmt->fetchColumn();

}

$in  = $a['check_in'] ?? null;
$out = $a['check_out'] ?? null;

$can_in  = empty($in) && !$lv;
$can_out = (!empty($in) && empty($out)) && !$lv;
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>值勤</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <?php require 'ui.php'; nav_top('值勤'); ?>
  <div class="wrap" style="max-width:720px;">
    <div class="card">
      <div class="muted">日期：<?= h($d) ?></div>

      <div class="grid2">
        <div class="card" style="margin-top:12px;">
          <h2 class="h2">值勤開始</h2>
          <div class="t"><?= h($in ?? '-') ?></div>
          <form method="post">
            <input type="hidden" name="act" value="in">
            <button class="btn primary" type="submit" style="width:100%;" <?= $can_in ? '' : 'disabled' ?>>值勤開始值勤</button>
          </form>
        </div>

        <div class="card" style="margin-top:12px;">
          <h2 class="h2">值勤結束</h2>
          <div class="t"><?= h($out ?? '-') ?></div>
          <form method="post">
            <input type="hidden" name="act" value="out">
            <button class="btn primary" type="submit" style="width:100%;" <?= $can_out ? '' : 'disabled' ?>>值勤結束值勤</button>
          </form>
        </div>
      </div>

      <?php if($msg): ?>
        <p class="msg <?= (str_contains($msg,'成功') ? 'ok' : '') ?>" style="margin-top:12px;"><?= h($msg) ?></p>
      <?php endif; ?>

      <?php if(!empty($lv)): ?>
        <div style="margin-top:12px;">
          <?= badge('今日請假（已核准）','info') ?>
          <span class="muted">請假期間內不需值勤打卡</span>
        </div>
      <?php endif; ?>

      <?php if(is_admin()): ?>
        <div style="margin-top:12px;">
          <?= badge('管理者', 'ok') ?>
          <span class="muted">可到「值勤總覽」查看/修正</span>
        </div>
      <?php endif; ?>
    </div>
  </div>
</body>
</html>
