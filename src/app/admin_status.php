<?php
require 'admin_only.php';
require 'db.php';
require_once 'ui.php';

date_default_timezone_set('Asia/Taipei');

function can_manage_row($me_role, $target_role){
  if ($me_role==='boss') return true;
  if ($me_role==='admin') return ($target_role==='employee');
  return false;
}

$d = $_POST['d'] ?? ($_GET['d'] ?? date('Y-m-d'));
$q = trim($_GET['q'] ?? '');
$me_role = $_SESSION['role'] ?? 'employee';

// 1) quick attendance action (start/end/clear)
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $uid = (int)($_POST['uid'] ?? 0);
  $act2 = $_POST['act2'] ?? '';
  if ($uid > 0 && in_array($act2, ['start','end','clear'], true)) {
    $stmt = $pdo->prepare("SELECT role FROM users WHERE user_id=? LIMIT 1");
    $stmt->execute([$uid]);
    $trole = $stmt->fetchColumn() ?: '';
    if (can_manage_user($trole, $uid)) {
      try {
        $pdo->beginTransaction();
        $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? FOR UPDATE");
        $stmt->execute([$uid, $d]);
        $row = $stmt->fetch();

        if ($act2 === 'clear') {
          if ($row) {
            $del = $pdo->prepare("DELETE FROM attendance WHERE att_id=?");
            $del->execute([(int)$row['att_id']]);
          }
        } elseif ($act2 === 'start') {
          $now = date('Y-m-d H:i:s');
          if (!$row) {
            $ins = $pdo->prepare("INSERT INTO attendance(user_id, work_date, check_in, status) VALUES(?,?,?,'open')");
            $ins->execute([$uid, $d, $now]);
          } else if (empty($row['check_in'])) {
            $upd = $pdo->prepare("UPDATE attendance SET check_in=?, status='open' WHERE att_id=?");
            $upd->execute([$now, (int)$row['att_id']]);
          }
        } elseif ($act2 === 'end') {
          $now = date('Y-m-d H:i:s');
          if ($row && !empty($row['check_in']) && empty($row['check_out'])) {
            $upd = $pdo->prepare("UPDATE attendance SET check_out=?, status='done' WHERE att_id=?");
            $upd->execute([$now, (int)$row['att_id']]);
          }
        }

        $pdo->commit();
      } catch (Exception $e) {
        $pdo->rollBack();
      }
    }
  }

  // 2) toggle active
  $uid3 = (int)($_POST['uid3'] ?? 0);
  if ($uid3 > 0 && (($_POST['act3'] ?? '') === 'toggle_active')) {
    $stmt = $pdo->prepare("SELECT role, is_active FROM users WHERE user_id=? LIMIT 1");
    $stmt->execute([$uid3]);
    $tu = $stmt->fetch();
    if ($tu) {
      $trole3 = $tu['role'] ?? '';
      $tis3 = (int)($tu['is_active'] ?? 0);
      if (can_manage_user($trole3, $uid3)) {
        // avoid disabling last boss
        if ($trole3==='boss' && $tis3===1) {
          $cnt = (int)$pdo->query("SELECT COUNT(*) FROM users WHERE role='boss' AND is_active=1")->fetchColumn();
          if ($cnt <= 1) {
            // keep at least one boss
          } else {
            $stmt = $pdo->prepare("UPDATE users SET is_active = IF(is_active=1,0,1) WHERE user_id=?");
            $stmt->execute([$uid3]);
          }
        } else {
          $stmt = $pdo->prepare("UPDATE users SET is_active = IF(is_active=1,0,1) WHERE user_id=?");
          $stmt->execute([$uid3]);
        }
      }
    }
  }
}

// attendance map
$stmt = $pdo->prepare("SELECT user_id, check_in, check_out, status FROM attendance WHERE work_date=?");
$stmt->execute([$d]);
$map = [];
foreach ($stmt->fetchAll() as $a) {
  $map[(int)$a['user_id']] = $a;
}

// approved leave map for date
$stmt = $pdo->prepare("SELECT user_id, leave_type FROM leaves WHERE status='approved' AND date_from<=? AND date_to>=?");
$stmt->execute([$d, $d]);
$lmap = [];
foreach ($stmt->fetchAll() as $x) {
  $lmap[(int)$x['user_id']] = $x['leave_type'];
}

// users list
$sql = "SELECT user_id, username, full_name, role, is_active FROM users";
$par = [];
if ($q !== '') { $sql .= " WHERE username LIKE ? OR full_name LIKE ?"; $par = ["%{$q}%","%{$q}%"]; }
$sql .= " ORDER BY user_id ASC";
$stmt = $pdo->prepare($sql);
$stmt->execute($par);
$u = $stmt->fetchAll();
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>勤務總覽 · 海事勤務</title>
  <?php require_once 'ui.php'; style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php
    $actions = '<a class="btn ghost" href="admin_export.php?d='.h($d).'">'.icon_svg('download').'匯出日報表</a>';
    page_header(
      '勤務總覽',
      '查看任一日所有人員的值勤狀態，並可快速開始、結束或清除值勤紀錄；亦可進一步編輯。',
      'ADMIN · 管理',
      $actions
    );
    ?>

    <div class="card">
      <form method="get" class="filter-bar">
        <div>
          <label>日期</label>
          <input type="date" name="d" value="<?= h($d) ?>">
        </div>
        <div style="flex:2;">
          <label>搜尋帳號或姓名</label>
          <input name="q" value="<?= h($q) ?>" placeholder="輸入關鍵字後按套用">
        </div>
        <div class="filter-actions">
          <button class="btn primary" type="submit"><?= icon_svg("check") ?>套用</button>
        </div>
      </form>

      <table>
        <tr>
          <th>ID</th><th>username</th><th>姓名</th><th>啟用</th><th>狀態</th><th>值勤開始</th><th>值勤結束</th><th>快速</th><th>操作</th>
        </tr>
        <?php $me_role = $_SESSION['role'] ?? 'employee'; ?>
        <?php foreach($u as $x):
          $uid = (int)$x['user_id'];
          $trole = $x['role'] ?? 'employee';
          $can2 = can_manage_row($me_role, $trole);
          $a = $map[$uid] ?? null;
          $lv = $lmap[$uid] ?? null;

          $label = '未值勤'; $type = 'off';
          if ($lv) {
            $label = '請假';
            $type = 'info';
          }
          if (!$lv && $a && !empty($a['check_in']) && empty($a['check_out'])) { $label='值勤開始中'; $type='warn'; }
          if (!$lv && $a && !empty($a['check_out'])) { $label='已值勤結束'; $type='ok'; }
        ?>
          <tr>
            <td><?= h($uid) ?></td>
            <td><?= h($x['username']) ?></td>
            <td><?= h($x['full_name']) ?></td>
            <td>
              <?= ((int)($x['is_active'] ?? 0)===1) ? badge('啟用','ok') : badge('停用','off') ?>
              <?php if($uid !== (int)($_SESSION['user_id'] ?? 0) || is_boss()): ?>
                <form method="post" style="margin-top:6px;">
                  <input type="hidden" name="act3" value="toggle_active">
                  <input type="hidden" name="uid3" value="<?= h($uid) ?>">
                  <button class="btn small" type="submit" <?= $can2?"":"disabled" ?>><?= ((int)($x['is_active'] ?? 0)===1) ? '停用' : '啟用' ?></button>
                <?php if(!$can2): ?><div class="muted">你沒有權限</div><?php endif; ?>
                </form>
              <?php else: ?>
                <div class="muted">（自己）</div><?php if(is_boss()): ?><div class="muted">boss 可管理自己</div><?php endif; ?>
              <?php endif; ?>
            </td>
            <td><?= badge($label, $type) ?></td>
            <td><?= h($a['check_in'] ?? '-') ?></td>
            <td><?= h($a['check_out'] ?? '-') ?></td>
            <td>
              <?php $can = can_manage_user(($x["role"] ?? ""), (int)$uid); ?>
              <form method="post" style="display:flex;gap:6px;flex-wrap:wrap;">
                <input type="hidden" name="uid" value="<?= h($uid) ?>">
                <input type="hidden" name="d" value="<?= h($d) ?>">
                <button class="btn small primary" name="act2" value="start" type="submit" <?= $can2?"":"disabled" ?>><?= icon_svg("check") ?>開始</button>
                <button class="btn small primary" name="act2" value="end" type="submit" <?= $can2?"":"disabled" ?>><?= icon_svg("clock") ?>結束</button>
                <button class="btn small" name="act2" value="clear" type="submit" <?= $can2?"":"disabled" ?>><?= icon_svg("trash") ?>清除</button>
              </form>
            </td>
            <td><?php if($can): ?>
              <a class="btn small" href="admin_edit.php?uid=<?= h($uid) ?>&d=<?= h($d) ?>"><?= icon_svg("edit") ?>編輯</a>
            <?php else: ?>
              <span class="btn small disabled" title="你沒有權限"><?= icon_svg("edit") ?>編輯</span>
              <span class="hint">你沒有權限</span>
            <?php endif; ?></td>
          </tr>
        <?php endforeach; ?>
      </table>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>