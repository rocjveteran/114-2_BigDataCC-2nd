<?php
require 'admin_only.php';
require 'db.php';
require_once 'ui.php';

date_default_timezone_set('Asia/Taipei');

$aid = (int)($_SESSION['user_id'] ?? 0);
$msg = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $id = (int)($_POST['id'] ?? 0);
  $act = $_POST['act'] ?? '';

  if ($id > 0 && in_array($act, ['approve','reject'], true)) {
    // permission: boss can approve/reject anyone; admin can approve/reject employee only
    $stmt = $pdo->prepare("SELECT u.role, u.user_id FROM leaves l JOIN users u ON u.user_id=l.user_id WHERE l.leave_id=? LIMIT 1");
    $stmt->execute([$id]);
    $t = $stmt->fetch();

    $trole = $t['role'] ?? '';
    $tid   = (int)($t['user_id'] ?? 0);

    if (!$t || !can_manage_user($trole, $tid)) {
      $msg = '你沒有權限';
    } else {
      $st = ($act === 'approve') ? 'approved' : 'rejected';
      try {
        $stmt = $pdo->prepare("UPDATE leaves SET status=?, decided_by=?, decided_at=NOW()
                               WHERE leave_id=? AND status='pending'");
        $stmt->execute([$st, $aid, $id]);
        $msg = "已更新";
      } catch (Exception $e) {
        $msg = "更新失敗";
      }
    }
  }
}

$q = $_GET['q'] ?? '';
$only = $_GET['only'] ?? 'pending';

$sql = "SELECT l.leave_id, l.user_id, u.username, u.full_name, l.date_from, l.date_to, l.leave_type, l.reason, l.status, l.created_at
        FROM leaves l JOIN users u ON u.user_id=l.user_id";
$where = [];
$par = [];

if ($only === 'pending' || $only === 'approved' || $only === 'rejected') {
  $where[] = "l.status=?";
  $par[] = $only;
}
if ($q !== '') {
  $where[] = "(u.username LIKE ? OR u.full_name LIKE ?)";
  $par[] = "%{$q}%";
  $par[] = "%{$q}%";
}
if ($where) $sql .= " WHERE " . implode(" AND ", $where);
$sql .= " ORDER BY l.leave_id DESC LIMIT 200";

$stmt = $pdo->prepare($sql);
$stmt->execute($par);
$rows = $stmt->fetchAll();

function type_name($t){
  if ($t === 'personal') return '事假';
  if ($t === 'sick') return '病假';
  return '其他';
}
function st_badge($st){
  if ($st === 'approved') return badge('已核准','ok');
  if ($st === 'rejected') return badge('已拒絕','bad');
  return badge('待審核','warn');
}
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>請假審核 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>

  <div class="wrap">
    <?php page_header(
      '請假審核',
      '核准或拒絕請假申請。boss 可審核所有人，admin 僅能審核 employee。',
      'ADMIN · 管理'
    ); ?>

    <?php if ($msg): ?>
      <p class="msg ok"><?= h($msg) ?></p>
    <?php endif; ?>

    <div class="card">
      <form method="get" class="filter-bar">
        <div>
          <label>狀態</label>
          <select name="only">
            <option value="pending"  <?= $only==='pending'?'selected':''  ?>>待審核</option>
            <option value="approved" <?= $only==='approved'?'selected':'' ?>>已核准</option>
            <option value="rejected" <?= $only==='rejected'?'selected':'' ?>>已拒絕</option>
          </select>
        </div>
        <div style="flex:2;">
          <label>搜尋</label>
          <input name="q" value="<?= h($q) ?>" placeholder="帳號或姓名">
        </div>
        <div class="filter-actions">
          <button class="btn primary" type="submit"><?= icon_svg('list') ?>查詢</button>
        </div>
      </form>

      <table>
        <tr>
          <th>ID</th>
          <th>人員</th>
          <th>期間</th>
          <th>假別</th>
          <th>狀態</th>
          <th>原因</th>
          <th>操作</th>
        </tr>

        <?php foreach ($rows as $x): ?>
          <tr>
            <td><?= h($x['leave_id']) ?></td>
            <td><?= h($x['username']) ?>（<?= h($x['full_name']) ?>）</td>
            <td><?= h($x['date_from']) ?> ~ <?= h($x['date_to']) ?></td>
            <td><?= h(type_name($x['leave_type'])) ?></td>
            <td><?= st_badge($x['status']) ?></td>
            <td><?= h($x['reason'] ?? '') ?></td>
            <td>
              <?php if ($x['status'] === 'pending'): ?>
                <form method="post" style="display:flex;gap:8px;flex-wrap:wrap;">
                  <input type="hidden" name="id" value="<?= h($x['leave_id']) ?>">

                  <button class="btn small okfill" name="act" value="approve" type="submit">
                    <?= icon_svg('check') ?>核准
                  </button>

                  <button class="btn small danger" name="act" value="reject" type="submit">
                    <?= icon_svg('x') ?>拒絕
                  </button>
                </form>
              <?php else: ?>
                <span class="muted">-</span>
              <?php endif; ?>
            </td>
          </tr>
        <?php endforeach; ?>
      </table>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
