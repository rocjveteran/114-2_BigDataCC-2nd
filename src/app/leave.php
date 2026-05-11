<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

date_default_timezone_set('Asia/Taipei');

$uid = (int)$_SESSION['user_id'];
$msg = null;
$err = null;

if (($_POST['act'] ?? '') === 'cancel') {
  $id = (int)($_POST['id'] ?? 0);
  if ($id > 0) {
    try {
      $stmt = $pdo->prepare("DELETE FROM leaves WHERE leave_id=? AND user_id=? AND status='pending'");
      $stmt->execute([$id, $uid]);
      $msg = ($stmt->rowCount() > 0) ? '已取消申請' : '無法取消（可能已審核）';
    } catch (Exception $e) {
      $err = '取消失敗';
    }
  }
}

function ok_date($d){
  return (bool)preg_match('/^\d{4}-\d{2}-\d{2}$/', $d);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && (($_POST['act'] ?? '') !== 'cancel')) {
  $from = $_POST['from'] ?? '';
  $to   = $_POST['to'] ?? '';
  $type = $_POST['type'] ?? 'personal';
  $reason = trim($_POST['reason'] ?? '');

  if (!ok_date($from) || !ok_date($to)) {
    $err = "日期格式錯誤";
  } elseif ($to < $from) {
    $err = "結束日期不可早於開始日期";
  } elseif (!in_array($type, ['personal','sick','other'], true)) {
    $err = "假別不合法";
  } else {
    try {
      $stmt = $pdo->prepare("INSERT INTO leaves(user_id, date_from, date_to, leave_type, reason, status) VALUES(?,?,?,?,?,'pending')");
      $stmt->execute([$uid, $from, $to, $type, ($reason === '' ? null : $reason)]);
      $msg = "已送出請假申請（待審核）";
    } catch (Exception $e) {
      $err = "送出失敗（請重試）";
    }
  }
}

$stmt = $pdo->prepare("SELECT leave_id, date_from, date_to, leave_type, reason, status, created_at
                       FROM leaves WHERE user_id=? ORDER BY leave_id DESC LIMIT 50");
$stmt->execute([$uid]);
$rows = $stmt->fetchAll();
$count = count($rows);

function type_name($t){
  if ($t==='personal') return '事假';
  if ($t==='sick') return '病假';
  return '其他';
}
function st_badge($st){
  if ($st==='approved') return badge('已核准','ok');
  if ($st==='rejected') return badge('已拒絕','bad');
  return badge('待審核','warn');
}
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>請假 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php page_header(
      '請假申請',
      '填寫日期區間與假別送出後，由 admin 或 boss 審核。狀態為「待審核」時可自行取消。',
      'LEAVE · 請假'
    ); ?>

    <?php if($msg): ?><p class="msg ok"><?= h($msg) ?></p><?php endif; ?>
    <?php if($err): ?><p class="msg err"><?= h($err) ?></p><?php endif; ?>

    <div class="card">
      <div class="card-head" style="border:0;padding:0;margin:0 0 14px;">
        <h2>新申請</h2>
        <span class="meta">送出後狀態為「待審核」</span>
      </div>

      <form method="post">
        <div class="row">
          <div>
            <label>開始日期</label>
            <input type="date" name="from" required value="<?= h(date('Y-m-d')) ?>">
          </div>
          <div>
            <label>結束日期</label>
            <input type="date" name="to" required value="<?= h(date('Y-m-d')) ?>">
          </div>
        </div>

        <div class="row">
          <div>
            <label>假別</label>
            <select name="type">
              <option value="personal">事假</option>
              <option value="sick">病假</option>
              <option value="other">其他</option>
            </select>
          </div>
          <div>
            <label>原因（可空白）</label>
            <input name="reason" placeholder="例如：就醫 / 私事">
          </div>
        </div>

        <div class="form-actions">
          <button class="btn primary" type="submit"><?= icon_svg('plus') ?>送出申請</button>
        </div>
      </form>
    </div>

    <div class="card">
      <div class="card-head" style="border:0;padding:0;margin:0 0 8px;">
        <h2>我的申請</h2>
        <span class="meta">最近 <?= (int)$count ?> 筆</span>
      </div>

      <?php if ($count === 0): ?>
        <p class="muted" style="padding:20px 0;">尚無請假紀錄。</p>
      <?php else: ?>
      <table>
        <tr><th>ID</th><th>期間</th><th>假別</th><th>狀態</th><th>原因</th><th>建立</th><th>操作</th></tr>
        <?php foreach($rows as $x): ?>
          <tr>
            <td><?= h($x['leave_id']) ?></td>
            <td><?= h($x['date_from']) ?> ～ <?= h($x['date_to']) ?></td>
            <td><?= h(type_name($x['leave_type'])) ?></td>
            <td><?= st_badge($x['status']) ?></td>
            <td class="muted"><?= h($x['reason'] ?? '') ?></td>
            <td class="muted"><?= h($x['created_at']) ?></td>
            <td>
              <?php if($x['status']==='pending'): ?>
                <form method="post" style="margin:0;">
                  <input type="hidden" name="act" value="cancel">
                  <input type="hidden" name="id" value="<?= h($x['leave_id']) ?>">
                  <button class="btn small danger" type="submit"><?= icon_svg('x') ?>取消</button>
                </form>
              <?php else: ?>
                <span class="muted">—</span>
              <?php endif; ?>
            </td>
          </tr>
        <?php endforeach; ?>
      </table>
      <?php endif; ?>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
