<?php
require 'admin_only.php';
require 'db.php';
require_once 'ui.php';

date_default_timezone_set('Asia/Taipei');

$uid = (int)($_GET['uid'] ?? 0);
$d   = $_GET['d'] ?? date('Y-m-d');

if ($uid <= 0) { http_response_code(400); echo "bad uid"; exit; }

// user
$stmt = $pdo->prepare("SELECT user_id, username, full_name, role FROM users WHERE user_id=? LIMIT 1");
$stmt->execute([$uid]);
$u = $stmt->fetch();
if (!$u) { http_response_code(404); echo 'not found'; exit; }
if (!can_manage_user($u['role'], (int)$u['user_id'])) { http_response_code(403); echo '你沒有權限'; exit; }

// attendance
$stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
$stmt->execute([$uid, $d]);
$a = $stmt->fetch();

$msg = null;
$err = null;

function to_dt($s) {
  $s = trim($s ?? '');
  if ($s === '') return null;
  // accept "YYYY-MM-DDTHH:MM" or "YYYY-MM-DD HH:MM"
  $s = str_replace('T', ' ', $s);
  if (preg_match('/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/', $s)) $s .= ':00';
  if (!preg_match('/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/', $s)) return false;
  return $s;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  csrf_require();
  $in_s  = to_dt($_POST['in'] ?? '');
  $out_s = to_dt($_POST['out'] ?? '');

  if ($in_s === false || $out_s === false) {
    $err = "時間格式錯誤（請用日期時間選擇器）";
  } else {
    try {
      // decide status
      $st = 'open';
      if ($out_s) $st = 'done';
      if (!$in_s && !$out_s) $st = 'open';

      $pdo->beginTransaction();

      // lock row
      $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? FOR UPDATE");
      $stmt->execute([$uid, $d]);
      $row = $stmt->fetch();

      if (!$in_s && !$out_s) {
        // if both empty -> delete record (clean)
        if ($row) {
          $del = $pdo->prepare("DELETE FROM attendance WHERE att_id=?");
          $del->execute([(int)$row['att_id']]);
        }
        $msg = "已清除該日值勤資料";
      } else {
        if (!$row) {
          $ins = $pdo->prepare("INSERT INTO attendance(user_id, work_date, check_in, check_out, status) VALUES(?,?,?,?,?)");
          $ins->execute([$uid, $d, $in_s, $out_s, $st]);
          $msg = "已建立/更新";
        } else {
          $upd = $pdo->prepare("UPDATE attendance SET check_in=?, check_out=?, status=? WHERE att_id=?");
          $upd->execute([$in_s, $out_s, $st, (int)$row['att_id']]);
          $msg = "已更新";
        }
      }

      $pdo->commit();
    } catch (Exception $e) {
      $pdo->rollBack();
      $err = "更新失敗";
    }
  }

  // reload
  $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
  $stmt->execute([$uid, $d]);
  $a = $stmt->fetch();
}

$in_v  = $a['check_in'] ?? '';
$out_v = $a['check_out'] ?? '';

function to_local($dt) {
  if (!$dt) return '';
  return str_replace(' ', 'T', substr($dt, 0, 16)); // datetime-local to minutes
}
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>編輯值勤 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap mid">
    <?php
    $actions = '<a class="btn ghost" href="admin_status.php?d='.h($d).'">'.icon_svg('list').'回勤務總覽</a>';
    page_header(
      '編輯值勤紀錄',
      $u['full_name'].'（'.$u['username'].'） · '.$d.'。可直接修改開始/結束時間，或清空兩欄並儲存以刪除該日紀錄。',
      'ADMIN · 管理',
      $actions
    );
    ?>

    <?php if($msg): ?><p class="msg ok"><?= h($msg) ?></p><?php endif; ?>
    <?php if($err): ?><p class="msg err"><?= h($err) ?></p><?php endif; ?>

    <div class="card">
      <form method="post">
        <?= csrf_input() ?>
        <div class="row">
          <div>
            <label>值勤開始時間</label>
            <input type="datetime-local" name="in" value="<?= h(to_local($in_v)) ?>">
          </div>
          <div>
            <label>值勤結束時間</label>
            <input type="datetime-local" name="out" value="<?= h(to_local($out_v)) ?>">
          </div>
        </div>

        <div class="form-actions">
          <button class="btn primary" type="submit"><?= icon_svg('check') ?>儲存</button>
          <a class="btn ghost" href="admin_status.php?d=<?= h($d) ?>">取消</a>
        </div>
        <div class="muted" style="margin-top:14px;font-size:13px;">
          提示：清空兩個時間欄並按儲存 = 刪除該日紀錄（回到「未值勤」）。
        </div>
      </form>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>