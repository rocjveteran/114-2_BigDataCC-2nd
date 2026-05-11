<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

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
        $msg = "值勤開始：{$now}";
      } else if (empty($row['check_in'])) {
        $upd = $pdo->prepare("UPDATE attendance SET check_in=?, status='open' WHERE att_id=?");
        $upd->execute([$now, (int)$row['att_id']]);
        $msg = "值勤開始：{$now}";
      } else {
        $msg = "已值勤開始，不能重複。";
      }
    } elseif ($act === 'out') {
      if (!$row || empty($row['check_in'])) {
        $msg = "尚未值勤開始，不能結束。";
      } else if (!empty($row['check_out'])) {
        $msg = "已值勤結束，不能重複。";
      } else {
        $upd = $pdo->prepare("UPDATE attendance SET check_out=?, status='done' WHERE att_id=?");
        $upd->execute([$now, (int)$row['att_id']]);
        $msg = "值勤結束：{$now}";
      }
    }

    $pdo->commit();
  } catch (Exception $e) {
    $pdo->rollBack();
    $msg = "操作失敗（請重試）";
  }

  $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
  $stmt->execute([$uid, $d]);
  $a = $stmt->fetch();

  $stmt = $pdo->prepare("SELECT leave_type FROM leaves WHERE user_id=? AND status='approved' AND date_from<=? AND date_to>=? LIMIT 1");
  $stmt->execute([$uid, $d, $d]);
  $lv = $stmt->fetchColumn();
}

$in  = $a['check_in'] ?? null;
$out = $a['check_out'] ?? null;

$can_in  = empty($in) && !$lv;
$can_out = (!empty($in) && empty($out)) && !$lv;

$weekday_zh = ['日','一','二','三','四','五','六'];
$wd = $weekday_zh[(int)date('w')];
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>值勤 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap mid">
    <?php page_header(
      '今日值勤',
      $d.' · 星期'.$wd.'。請依勤務開始與結束時間打卡，結束後資料即進入「我的紀錄」。',
      'TODAY · 今日'
    ); ?>

    <?php if(!empty($lv)): ?>
      <div class="msg" style="background:rgba(42,90,153,.06);border-color:rgba(42,90,153,.22);color:var(--info)">
        <strong>今日已核准請假</strong> — 請假期間內不需打卡。
      </div>
    <?php endif; ?>

    <?php if($msg): ?>
      <?php
        $cls = '';
        if (str_contains($msg,'開始：') || str_contains($msg,'結束：')) $cls = 'ok';
        elseif (str_contains($msg,'不能') || str_contains($msg,'失敗') || str_contains($msg,'尚未')) $cls = 'err';
      ?>
      <p class="msg <?= $cls ?>"><?= h($msg) ?></p>
    <?php endif; ?>

    <div class="grid2">
      <div class="card">
        <div class="card-head">
          <h2>值勤開始</h2>
          <?php if(!empty($in)): ?><span class="badge ok">已打卡</span><?php else: ?><span class="badge off">尚未開始</span><?php endif; ?>
        </div>
        <div class="t serif"><?= h($in ?? '—') ?></div>
        <form method="post" style="margin-top:8px;">
          <input type="hidden" name="act" value="in">
          <button class="btn primary" type="submit" style="width:100%;" <?= $can_in ? '' : 'disabled' ?>>
            <?= icon_svg('clock') ?>開始值勤
          </button>
        </form>
      </div>

      <div class="card">
        <div class="card-head">
          <h2>值勤結束</h2>
          <?php if(!empty($out)): ?><span class="badge ok">已結束</span><?php elseif(!empty($in)): ?><span class="badge warn">值勤中</span><?php else: ?><span class="badge off">尚未開始</span><?php endif; ?>
        </div>
        <div class="t serif"><?= h($out ?? '—') ?></div>
        <form method="post" style="margin-top:8px;">
          <input type="hidden" name="act" value="out">
          <button class="btn primary" type="submit" style="width:100%;" <?= $can_out ? '' : 'disabled' ?>>
            <?= icon_svg('check') ?>結束值勤
          </button>
        </form>
      </div>
    </div>

    <?php if(is_admin()): ?>
      <div class="muted" style="margin-top:18px;font-size:13px;">
        管理者可至 <a class="inline" href="admin_status.php">勤務總覽</a> 查看與修正全員值勤。
      </div>
    <?php endif; ?>
  </div>
  <?php page_footer(); ?>
</body>
</html>
