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
  if (!$can) {
    $err = '你沒有權限';
  } else {
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
}
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>修改帳號 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap mid">
    <?php
    $actions = '<a class="btn ghost" href="admin_users.php">'.icon_svg('users').'回帳號管理</a>';
    page_header(
      '修改帳號',
      'ID #'.h($u['user_id']).' · '.h(role_name($u['role'])).' · 建立於 '.h($u['created_at']),
      'ADMIN · 管理',
      $actions
    );
    ?>

    <?php if(!$can): ?><p class="msg err">你沒有權限（只可查看）</p><?php endif; ?>
    <?php if($msg): ?><p class="msg ok"><?= h($msg) ?></p><?php endif; ?>
    <?php if($err): ?><p class="msg err"><?= h($err) ?></p><?php endif; ?>

    <div class="card">
      <form method="post">
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
              <label>角色</label>
              <?php if($my_role==='boss'): ?>
                <select name="role">
                  <option value="boss"     <?= $u['role']==='boss'?'selected':'' ?>>boss（老闆）</option>
                  <option value="admin"    <?= $u['role']==='admin'?'selected':'' ?>>admin（管理員）</option>
                  <option value="employee" <?= $u['role']==='employee'?'selected':'' ?>>employee（員工）</option>
                </select>
              <?php else: ?>
                <select disabled>
                  <option selected>employee（員工）</option>
                </select>
                <div class="muted" style="margin-top:6px;font-size:12.5px;">你沒有權限調整角色</div>
              <?php endif; ?>
            </div>
            <div>
              <label>啟用狀態</label>
              <label class="check-label">
                <input type="checkbox" name="is_active" <?= ((int)$u['is_active']===1)?'checked':'' ?> style="width:auto;">
                <?= ((int)$u['is_active']===1) ? '帳號啟用中' : '帳號已停用' ?>
              </label>
            </div>
          </div>

          <label>重設密碼（留空表示不變）</label>
          <input name="newpw" type="password" placeholder="留空 = 不修改密碼">

          <div class="form-actions">
            <button class="btn primary" type="submit"><?= icon_svg('check') ?>儲存變更</button>
            <a class="btn ghost" href="admin_users.php">取消</a>
          </div>

          <?php if($my_role!=='boss'): ?>
            <div class="muted" style="margin-top:14px;font-size:13px;">admin 僅能管理 employee；如需調整其他角色請聯絡 boss。</div>
          <?php endif; ?>
        </fieldset>
      </form>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>