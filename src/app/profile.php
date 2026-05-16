<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

date_default_timezone_set('Asia/Taipei');

$uid = (int)$_SESSION['user_id'];

$stmt = $pdo->prepare("SELECT user_id, username, full_name, role, duty_position, is_active, created_at FROM users WHERE user_id=? LIMIT 1");
$stmt->execute([$uid]);
$u = $stmt->fetch();
if (!$u) { http_response_code(404); echo 'not found'; exit; }

// Lifetime totals
$stmt = $pdo->prepare("SELECT COUNT(*) AS days, SUM(TIMESTAMPDIFF(MINUTE, check_in, check_out)) AS mins
                       FROM attendance WHERE user_id=? AND check_in IS NOT NULL AND check_out IS NOT NULL");
$stmt->execute([$uid]);
$tot = $stmt->fetch();
$tot_hours = $tot['mins'] ? round($tot['mins']/60, 1) : 0;
$tot_days  = (int)($tot['days'] ?? 0);

// This month
$stmt = $pdo->prepare("SELECT COUNT(*) AS days, SUM(TIMESTAMPDIFF(MINUTE, check_in, check_out)) AS mins
                       FROM attendance WHERE user_id=? AND work_date BETWEEN ? AND ?
                         AND check_in IS NOT NULL AND check_out IS NOT NULL");
$stmt->execute([$uid, date('Y-m-01'), date('Y-m-t')]);
$mo = $stmt->fetch();
$mo_hours = $mo['mins'] ? round($mo['mins']/60, 1) : 0;
$mo_days  = (int)($mo['days'] ?? 0);

// Leave stats
$stmt = $pdo->prepare("SELECT status, COUNT(*) c FROM leaves WHERE user_id=? GROUP BY status");
$stmt->execute([$uid]);
$lv_counts = ['pending'=>0,'approved'=>0,'rejected'=>0];
foreach ($stmt->fetchAll() as $r) $lv_counts[$r['status']] = (int)$r['c'];

// Recent 6 attendance
$stmt = $pdo->prepare("SELECT work_date, check_in, check_out, duty_zone, sea_state, TIMESTAMPDIFF(MINUTE, check_in, check_out) AS mins
                       FROM attendance WHERE user_id=? ORDER BY work_date DESC LIMIT 6");
$stmt->execute([$uid]);
$recent = $stmt->fetchAll();

// Position frequency
$stmt = $pdo->prepare("SELECT duty_zone, COUNT(*) c FROM attendance WHERE user_id=? AND duty_zone IS NOT NULL GROUP BY duty_zone ORDER BY c DESC LIMIT 4");
$stmt->execute([$uid]);
$zones = $stmt->fetchAll();
$zone_total = array_sum(array_column($zones, 'c'));
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>個人檔案 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php
    page_header(
      '個人檔案',
      '檢視您的職務資訊、累計值勤、近期紀錄與請假狀態。',
      'PROFILE · 檔案'
    );
    ?>

    <div class="card" style="display:flex;gap:20px;align-items:center;">
      <?= avatar_initial($u['full_name'], 56, 'primary') ?>
      <div style="flex:1;min-width:0;">
        <div style="font-family:var(--font-serif);font-size:26px;color:var(--text);letter-spacing:-0.3px;line-height:1.1;"><?= h($u['full_name']) ?></div>
        <div style="font-size:13px;color:var(--muted);margin-top:4px;">
          @<?= h($u['username']) ?> · <?= h(role_name($u['role'])) ?> · 駐勤位置 <strong style="color:var(--text-soft);"><?= h($u['duty_position']) ?></strong>
        </div>
        <div style="font-size:12.5px;color:var(--muted);margin-top:6px;">
          加入於 <?= h(substr($u['created_at'], 0, 10)) ?> · 帳號 <?= ((int)$u['is_active']===1) ? badge('啟用','ok') : badge('停用','off') ?>
        </div>
      </div>
    </div>

    <div class="stat-grid" style="margin-top:24px;">
      <div class="stat-card">
        <div class="stat-icon"><?= icon_svg('clock') ?></div>
        <div class="stat-lbl">累計時數</div>
        <div class="stat-num"><?= h($tot_hours) ?><span style="font-size:16px;color:var(--muted);font-family:var(--font-sans);">&nbsp;hr</span></div>
        <div class="stat-sub">值勤 <?= h($tot_days) ?> 天</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon"><?= icon_svg('calendar') ?></div>
        <div class="stat-lbl">本月</div>
        <div class="stat-num"><?= h($mo_hours) ?><span style="font-size:16px;color:var(--muted);font-family:var(--font-sans);">&nbsp;hr</span></div>
        <div class="stat-sub"><?= h($mo_days) ?> 天</div>
      </div>
      <div class="stat-card ok">
        <div class="stat-icon"><?= icon_svg('check') ?></div>
        <div class="stat-lbl">核准請假</div>
        <div class="stat-num"><?= h($lv_counts['approved']) ?></div>
        <div class="stat-sub">次</div>
      </div>
      <div class="stat-card warn">
        <div class="stat-icon"><?= icon_svg('plane') ?></div>
        <div class="stat-lbl">待批請假</div>
        <div class="stat-num"><?= h($lv_counts['pending']) ?></div>
        <div class="stat-sub">次 · 拒絕 <?= h($lv_counts['rejected']) ?> 次</div>
      </div>
    </div>

    <div class="grid2">
      <div class="card">
        <div class="card-head">
          <h2>近期值勤</h2>
          <a href="records.php" class="muted" style="font-size:12.5px;">查看全部 →</a>
        </div>
        <?php if (!$recent): ?>
          <div class="muted" style="padding:18px 0;font-size:13px;">尚無值勤紀錄。</div>
        <?php else: ?>
          <table>
            <tr><th>日期</th><th>時數</th><th>海域</th><th>海象</th></tr>
            <?php foreach ($recent as $r):
              $hh = $r['mins'] ? round($r['mins']/60, 1) : 0;
            ?>
              <tr>
                <td><?= h($r['work_date']) ?></td>
                <td><?= h($hh) ?> hr</td>
                <td><?= $r['duty_zone'] ? h($r['duty_zone']) : '<span class="muted">—</span>' ?></td>
                <td><?= $r['sea_state'] ? h($r['sea_state']) : '<span class="muted">—</span>' ?></td>
              </tr>
            <?php endforeach; ?>
          </table>
        <?php endif; ?>
      </div>

      <div class="card">
        <div class="card-head">
          <h2>常駐海域</h2>
          <span class="muted" style="font-size:12.5px;">累計分布</span>
        </div>
        <?php if (!$zones): ?>
          <div class="muted" style="padding:18px 0;font-size:13px;">尚無海域資料。</div>
        <?php else: foreach ($zones as $z):
          $pct = $zone_total>0 ? round($z['c']/$zone_total*100) : 0;
        ?>
          <div style="margin:14px 0;">
            <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px;">
              <span style="font-weight:600;color:var(--text);"><?= h($z['duty_zone']) ?></span>
              <span class="muted"><?= h($z['c']) ?> 次 · <?= h($pct) ?>%</span>
            </div>
            <div style="height:6px;background:var(--bg-alt);border-radius:3px;overflow:hidden;">
              <div style="height:100%;width:<?= h($pct) ?>%;background:var(--primary);"></div>
            </div>
          </div>
        <?php endforeach; endif; ?>
        <div class="muted" style="margin-top:14px;font-size:12.5px;">
          目前駐勤位置：<strong style="color:var(--text-soft);"><?= h($u['duty_position']) ?></strong>。如需變更請聯絡管理者。
        </div>
      </div>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
