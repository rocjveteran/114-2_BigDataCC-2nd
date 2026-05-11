<?php
require 'admin_only.php';
require 'db.php';
require_once 'ui.php';

date_default_timezone_set('Asia/Taipei');

$my_id = (int)($_SESSION['user_id'] ?? 0);
$my_role = $_SESSION['role'] ?? '';

$uid = (int)($_GET['uid'] ?? 0);
if ($uid <= 0) { http_response_code(400); echo "bad uid"; exit; }

$stmt = $pdo->prepare("SELECT user_id, username, full_name, role, is_active, created_at FROM users WHERE user_id=? LIMIT 1");
$stmt->execute([$uid]);
$u = $stmt->fetch();
if (!$u) { http_response_code(404); echo "user not found"; exit; }

$can = can_manage_user($u['role'], (int)$u['user_id']);

function boss_count($pdo){
  return (int)$pdo->query("SELECT COUNT(*) FROM users WHERE role='boss' AND is_active=1")->fetchColumn();
}

$msg = null;
$err = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  if (!$can) { $err = '你沒有權限'; }
  else 
  $username  = trim($_POST['username'] ?? '');
  $full_name = trim($_POST['full_name'] ?? '');
  $is_active = isset($_POST['is_active']) ? 1 : 0;
  $newpw     = $_POST['newpw'] ?? '';

  // role: only boss can change role; admin can only keep employee
  $role = $u['role'];
  if ($my_role === 'boss') {
    $role = $_POST['role'] ?? $u['role'];
    if (!in_array($role, ['boss','admin','employee'], true)) $role = $u['role'];
  } else {
    $role = 'employee';
  }

  if ($username === '' || $full_name === '') $err = "帳號/姓名不可空白";

  // avoid disabling / demoting last boss
  if (!$err && $u['role']==='boss' && (int)$u['is_active']===1) {
    $will_not_boss = ($role !== 'boss');
    $will_disable  = ($is_active === 0);
    if (($will_not_boss || $will_disable) && boss_count($pdo) <= 1) {
      $err = "不可移除/停用最後一個老闆";
    }
  }

  if (!$err) {
    try {
      if ($newpw !== '') {
        $hash = password_hash($newpw, PASSWORD_DEFAULT);
        $stmt = $pdo->prepare("UPDATE users SET username=?, full_name=?, role=?, is_active=?, password_hash=? WHERE user_id=?");
        $stmt->execute([$username, $full_name, $role, $is_active, $hash, $uid]);
      } else {
        $stmt = $pdo->prepare("UPDATE users SET username=?, full_name=?, role=?, is_active=? WHERE user_id=?");
        $stmt->execute([$username, $full_name, $role, $is_active, $uid]);
      }
      $msg = "已更新";
    } catch (Exception $e) {
      $err = "更新失敗（可能帳號重複）";
    }
  }

  // reload
  $stmt = $pdo->prepare("SELECT user_id, username, full_name, role, is_active, created_at FROM users WHERE user_id=? LIMIT 1");
  $stmt->execute([$uid]);
  $u = $stmt->fetch();
}
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>修改帳號</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <?php nav_top('修改帳號'); ?>
  <div class="wrap" style="max-width:820px;">
    <div class="card">
      <div class="muted">ID：<?= h($u['user_id']) ?>｜等級：<?= h(role_name($u['role'])) ?>｜建立時間：<?= h($u['created_at']) ?></div>

      <?php if(!$can): ?><p class="msg err" style="margin-top:10px;">你沒有權限（只可查看）</p><?php endif; ?>

      <?php if($msg): ?><p class="msg ok" style="margin-top:10px;"><?= h($msg) ?></p><?php endif; ?>
      <?php if($err): ?><p class="msg err" style="margin-top:10px;"><?= h($err) ?></p><?php endif; ?>

      <form method="post" style="margin-top:10px;">
        <fieldset <?= (!$can)?'disabled':'' ?> style="border:0;padding:0;margin:0;">
        <div class="row">
          <div>
            <label>帳號</label>
            <input name="username" value="<?= h($u['username']) ?>" placeholder="請輸入帳號" required>
          </div>
          <div>
            <label>姓名</label>
            <input name="full_name" value="<?= h($u['full_name']) ?>" placeholder="請輸入姓名" required>
          </div>
        </div>

        <div class="row">
          <div>
            <label>等級</label>
            <?php if($my_role==='boss'): ?>
              <select name="role">
                <option value="boss" <?= $u['role']==='boss'?'selected':'' ?>>boss</option>
                <option value="admin" <?= $u['role']==='admin'?'selected':'' ?>>admin</option>
                <option value="employee" <?= $u['role']==='employee'?'selected':'' ?>>employee</option>
              </select>
            <?php else: ?>
              <select disabled>
                <option selected>employee</option>
              </select>
              <div class="hint">你沒有權限調整等級</div>
            <?php endif; ?>
          </div>
          <div>
            <label>啟用</label>
            <label style="display:flex;gap:10px;align-items:center;margin-top:8px;">
              <input type="checkbox" name="is_active" <?= ((int)$u['is_active']===1)?'checked':'' ?> style="width:auto;">
              <?= ((int)$u['is_active']===1) ? '啟用' : '停用' ?>
            </label>
          </div>
        </div>

        <label>重設密碼（可空白）</label>
        <input name="newpw" type="password" placeholder="不修改就留空白">

        <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap;">
          <button class="btn primary" type="submit"><?= icon_svg('check') ?>儲存</button>
          <a class="btn" href="admin_users.php"><?= icon_svg('users') ?>回帳號管理</a>
        </div>

        <?php if($my_role!=='boss'): ?>
          <div class="muted" style="margin-top:10px;">管理員只能管理員工。</div>
        <?php endif; ?>
              </fieldset>
      </form>
    </div>
  </div>
</body>
</html>