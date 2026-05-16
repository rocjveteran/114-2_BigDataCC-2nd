<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

date_default_timezone_set('Asia/Taipei');

$today = date('Y-m-d');
$q = trim($_GET['q'] ?? '');
$pos_filter = trim($_GET['pos'] ?? '');
$status_filter = trim($_GET['status'] ?? '');

$sql = "
  SELECT u.user_id, u.username, u.full_name, u.role, u.duty_position, u.is_active,
         a.check_in, a.check_out,
         (SELECT leave_type FROM leaves lv
          WHERE lv.user_id=u.user_id AND lv.status='approved'
            AND lv.date_from<=? AND lv.date_to>=? LIMIT 1) AS lv_type,
         (SELECT COUNT(*) FROM attendance att
          WHERE att.user_id=u.user_id AND att.check_in IS NOT NULL AND att.check_out IS NOT NULL) AS lifetime_days,
         (SELECT ROUND(SUM(TIMESTAMPDIFF(MINUTE, att.check_in, att.check_out))/60, 1) FROM attendance att
          WHERE att.user_id=u.user_id AND att.check_in IS NOT NULL AND att.check_out IS NOT NULL) AS lifetime_hr
  FROM users u
  LEFT JOIN attendance a ON a.user_id=u.user_id AND a.work_date=?
  WHERE u.is_active=1
";
$par = [$today, $today, $today];
if ($q !== '') { $sql .= " AND (u.full_name LIKE ? OR u.username LIKE ?)"; $par[] = "%{$q}%"; $par[] = "%{$q}%"; }
if ($pos_filter !== '') { $sql .= " AND u.duty_position=?"; $par[] = $pos_filter; }
$sql .= " ORDER BY u.user_id";
$stmt = $pdo->prepare($sql);
$stmt->execute($par);
$crew = $stmt->fetchAll();

function crew_status($cr){
  if ($cr['lv_type'])                                                       return ['leave','請假','warn'];
  if (!empty($cr['check_in']) && empty($cr['check_out']))                   return ['on','值勤中','info'];
  if (!empty($cr['check_out']))                                             return ['done','已下勤','ok'];
  return ['off','未值勤','off'];
}

// Apply status filter post-fetch (simpler than complex SQL)
if ($status_filter !== '') {
  $crew = array_filter($crew, fn($c) => crew_status($c)[0] === $status_filter);
}

// Aggregate by position
$by_pos = [];
foreach ($crew as $c) {
  $p = $c['duty_position'] ?: '未指定';
  $by_pos[$p][] = $c;
}

// Get list of positions for filter dropdown
$positions = ['艦橋','瞭望台','前甲板','後甲板','通訊室','機艙'];

// Status totals
$cnt = ['on'=>0,'done'=>0,'leave'=>0,'off'=>0];
foreach ($crew as $c) { $cnt[crew_status($c)[0]]++; }
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>艦上人員 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php
    page_header(
      '艦上人員',
      '依職務位置檢視全艦人員與當前值勤狀態，可篩選海域、職務或搜尋姓名。',
      'CREW · 花名冊'
    );
    ?>

    <div class="card">
      <form method="get" class="filter-bar">
        <div>
          <label>搜尋</label>
          <input name="q" value="<?= h($q) ?>" placeholder="姓名 / 帳號">
        </div>
        <div>
          <label>職務位置</label>
          <select name="pos">
            <option value="">全部</option>
            <?php foreach ($positions as $p): ?>
              <option value="<?= h($p) ?>" <?= $pos_filter===$p?'selected':'' ?>><?= h($p) ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <div>
          <label>今日狀態</label>
          <select name="status">
            <option value="">全部</option>
            <option value="on"    <?= $status_filter==='on'?'selected':'' ?>>值勤中</option>
            <option value="done"  <?= $status_filter==='done'?'selected':'' ?>>已下勤</option>
            <option value="leave" <?= $status_filter==='leave'?'selected':'' ?>>請假</option>
            <option value="off"   <?= $status_filter==='off'?'selected':'' ?>>未值勤</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn primary" type="submit"><?= icon_svg('check') ?>套用</button>
          <a class="btn ghost" href="crew.php">重置</a>
        </div>
      </form>

      <div style="display:flex;gap:24px;flex-wrap:wrap;font-size:13px;padding:6px 0 14px;color:var(--muted);">
        <span>共 <strong style="color:var(--text);"><?= h(count($crew)) ?></strong> 人</span>
        <span><span class="ship-legend-dot on"></span> 值勤中 <strong style="color:var(--text);"><?= h($cnt['on']) ?></strong></span>
        <span><span class="ship-legend-dot done"></span> 已下勤 <strong style="color:var(--text);"><?= h($cnt['done']) ?></strong></span>
        <span><span class="ship-legend-dot leave"></span> 請假 <strong style="color:var(--text);"><?= h($cnt['leave']) ?></strong></span>
        <span><span class="ship-legend-dot off"></span> 未值勤 <strong style="color:var(--text);"><?= h($cnt['off']) ?></strong></span>
      </div>
    </div>

    <?php if (!$crew): ?>
      <div class="empty-state" style="margin-top:24px;">
        <h3>沒有符合條件的人員</h3>
        <p>請調整搜尋或篩選條件再試。</p>
      </div>
    <?php else: foreach ($by_pos as $pos => $list): ?>
      <h3 style="font-family:var(--font-serif);font-size:22px;font-weight:400;color:var(--text);margin:32px 0 12px;letter-spacing:-0.3px;">
        <?= h($pos) ?> <span style="color:var(--muted);font-size:14px;font-family:var(--font-sans);font-weight:500;">· <?= h(count($list)) ?> 人</span>
      </h3>
      <div class="roster-grid">
        <?php foreach ($list as $c):
          [$st, $st_zh, $st_type] = crew_status($c);
          $av_variant = match($st) { 'on'=>'primary', 'done'=>'ok', 'leave'=>'warn', default=>'off' };
        ?>
          <div class="roster-card">
            <?= avatar_initial($c['full_name'], 44, $av_variant) ?>
            <div class="rc-body">
              <div class="rc-name"><?= h($c['full_name']) ?></div>
              <div class="rc-meta">@<?= h($c['username']) ?> · <?= h(role_name($c['role'])) ?> · <?= badge($st_zh, $st_type) ?></div>
              <div class="rc-stats">
                累計 <strong style="color:var(--text-soft);"><?= h($c['lifetime_days'] ?? 0) ?></strong> 天 · <strong style="color:var(--text-soft);"><?= h($c['lifetime_hr'] ?? 0) ?></strong> hr
                <?php if (!empty($c['check_in'])): ?>
                  <br>今日 <?= h(substr($c['check_in'], 11, 5)) ?><?= !empty($c['check_out']) ? ' – '.h(substr($c['check_out'], 11, 5)) : '' ?>
                <?php endif; ?>
              </div>
            </div>
          </div>
        <?php endforeach; ?>
      </div>
    <?php endforeach; endif; ?>
  </div>
  <?php page_footer(); ?>
</body>
</html>
