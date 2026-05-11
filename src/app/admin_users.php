<?php
require 'auth.php';
require 'db.php';
require_once 'ui.php';

date_default_timezone_set('Asia/Taipei');

$my_id = (int)($_SESSION['user_id'] ?? 0);
$my_role = $_SESSION['role'] ?? '';
$msg = null;
$err = null;

function boss_count($pdo){
  return (int)$pdo->query("SELECT COUNT(*) FROM users WHERE role='boss' AND is_active=1")->fetchColumn();
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $act = $_POST['act'] ?? '';
  $uid = (int)($_POST['uid'] ?? 0);

  
  // permission guard
  $stmt = $pdo->prepare("SELECT role FROM users WHERE user_id=? LIMIT 1");
  $stmt->execute([$uid]);
  $trole = $stmt->fetchColumn();
  if (!$trole || !can_manage_user($trole, $uid)) {
    $err = "你沒有權限";
  } else {
if ($act === 'toggle' && $uid > 0) {
    $stmt = $pdo->prepare("SELECT user_id, role, is_active FROM users WHERE user_id=? LIMIT 1");
    $stmt->execute([$uid]);
    $t = $stmt->fetch();

    if (!$t) {
      $err = "找不到帳號";
    } else {
      $trole = $t['role'];
      $tis_active = (int)$t['is_active'];

      if (!can_manage_user($trole, (int)$t['user_id'])) {
        $err = "你沒有權限";
      } else {
        // avoid disabling last boss
        if ($trole === 'boss' && $tis_active === 1) {
          if (boss_count($pdo) <= 1) {
            $err = "不可停用最後一個老闆";
          }
        }

        if (!$err) {
          try {
            $stmt = $pdo->prepare("UPDATE users SET is_active = IF(is_active=1,0,1) WHERE user_id=?");
            $stmt->execute([$uid]);
            $msg = "已更新";
          } catch (Exception $e) {
            $err = "更新失敗";
          }
        }
      }
    }
  }
  }

}

$q = trim($_GET['q'] ?? '');
$sql = "SELECT user_id, username, full_name, role, is_active, created_at FROM users";
$par = [];
if ($q !== '') {
  $sql .= " WHERE username LIKE ? OR full_name LIKE ?";
  $par = ["%{$q}%","%{$q}%"];
}
$sql .= " ORDER BY user_id DESC LIMIT 200";

$stmt = $pdo->prepare($sql);
$stmt->execute($par);
$rows = $stmt->fetchAll();
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>帳號管理</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <?php nav_top('帳號管理'); ?>
  <div class="wrap">
    <div class="card">
      <div class="toolbar">
        <div>
          <div class="title">帳號清單</div>
          <div class="sub">搜尋、修改、啟用/停用（依權限顯示）</div>
        </div>
        <div class="actions">
          <form method="get" style="min-width:260px;">
            <input name="q" value="<?= h($q) ?>" placeholder="搜尋：帳號或姓名">
          </form>
          <a class="btn okfill" href="admin_create_user.php"><?= icon_svg("plus") ?>新增</a>
          <a class="btn" href="admin_status.php"><?= icon_svg("list") ?>值勤總覽</a>
        </div>
      </div>

      <?php if($msg): ?><p class="msg ok" style="margin-top:10px;"><?= h($msg) ?></p><?php endif; ?>
      <?php if($err): ?><p class="msg err" style="margin-top:10px;"><?= h($err) ?></p><?php endif; ?>

      <table>
        <tr><th>ID</th><th>帳號</th><th>姓名</th><th>等級</th><th>啟用</th><th>建立時間</th><th>操作</th></tr>
        <?php foreach($rows as $u): $uid=(int)$u['user_id']; $trole=$u['role']; $can = can_manage_user($trole, $uid); ?>
          <tr>
            <td><?= h($uid) ?></td>
            <td><?= h($u['username']) ?></td>
            <td><?= h($u['full_name']) ?></td>
            <td><?= h(role_name($trole)) ?></td>
            <td><?= ((int)$u['is_active']===1) ? badge('啟用','ok') : badge('停用','off') ?></td>
            <td><?= h($u['created_at']) ?></td>
            <td style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
              <?php if($can): ?>
                <a class="btn small" href="admin_user_edit.php?uid=<?= h($uid) ?>"><?= icon_svg('edit') ?>修改</a>
                <form method="post">
                  <input type="hidden" name="act" value="toggle">
                  <input type="hidden" name="uid" value="<?= h($uid) ?>">
                  <button class="btn small" type="submit"><?= ((int)$u['is_active']===1) ? '停用' : '啟用' ?></button>
                </form>
              <?php else: ?>
                <span class="btn small disabled" title="你沒有權限"><?= icon_svg('edit') ?>修改</span>
                <span class="btn small disabled" title="你沒有權限">停用/啟用</span>
                <span class="hint">你沒有權限</span>
              <?php endif; ?>
            </td>
          </tr>
        <?php endforeach; ?>
      </table>
    </div>
  </div>
</body>
</html>