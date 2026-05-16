<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

date_default_timezone_set('Asia/Taipei');

$from = $_GET['from'] ?? date('Y-m-d', strtotime('-30 days'));
$to   = $_GET['to']   ?? date('Y-m-d');
$zone_f = trim($_GET['zone'] ?? '');
$sea_f  = trim($_GET['sea']  ?? '');

// Validate dates
if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $from)) $from = date('Y-m-d', strtotime('-30 days'));
if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $to))   $to   = date('Y-m-d');

$sql = "
  SELECT a.work_date,
         GROUP_CONCAT(DISTINCT a.duty_zone ORDER BY a.duty_zone) AS zones,
         GROUP_CONCAT(DISTINCT a.sea_state ORDER BY a.sea_state) AS seas,
         COUNT(DISTINCT a.user_id) AS crew_count,
         SUM(TIMESTAMPDIFF(MINUTE, a.check_in, a.check_out)) AS total_mins,
         SUM(CASE WHEN a.check_out IS NOT NULL THEN 1 ELSE 0 END) AS done_count,
         GROUP_CONCAT(DISTINCT a.vessel_id ORDER BY a.vessel_id) AS vessels
  FROM attendance a
  WHERE a.work_date BETWEEN ? AND ?
    AND a.check_in IS NOT NULL
";
$par = [$from, $to];
if ($zone_f !== '') { $sql .= " AND a.duty_zone=?"; $par[] = $zone_f; }
if ($sea_f !== '')  { $sql .= " AND a.sea_state=?"; $par[] = $sea_f; }
$sql .= " GROUP BY a.work_date ORDER BY a.work_date DESC";
$stmt = $pdo->prepare($sql);
$stmt->execute($par);
$voyages = $stmt->fetchAll();

$wd_zh = ['日','一','二','三','四','五','六'];
$zone_cls = ['港口'=>'zone-port','近海'=>'zone-near','外海'=>'zone-far'];
$sea_cls  = ['平靜'=>'sea-calm','輕浪'=>'sea-light','中浪'=>'sea-med','大浪'=>'sea-rough'];

$total_crew = 0; $total_hours = 0;
foreach ($voyages as $v) { $total_crew += (int)$v['crew_count']; $total_hours += $v['total_mins'] ? round($v['total_mins']/60, 1) : 0; }
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>航次紀錄 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php
    page_header(
      '航次紀錄',
      '依日期彙整每日艦務：海域、海象、出勤人員與總時數。每一日視為一次航次活動。',
      'VOYAGES · 航次'
    );
    ?>

    <div class="card">
      <form method="get" class="filter-bar">
        <div>
          <label>起始日期</label>
          <input type="date" name="from" value="<?= h($from) ?>">
        </div>
        <div>
          <label>結束日期</label>
          <input type="date" name="to" value="<?= h($to) ?>">
        </div>
        <div>
          <label>海域</label>
          <select name="zone">
            <option value="">全部</option>
            <?php foreach (['港口','近海','外海'] as $z): ?>
              <option value="<?= h($z) ?>" <?= $zone_f===$z?'selected':'' ?>><?= h($z) ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <div>
          <label>海象</label>
          <select name="sea">
            <option value="">全部</option>
            <?php foreach (['平靜','輕浪','中浪','大浪'] as $s): ?>
              <option value="<?= h($s) ?>" <?= $sea_f===$s?'selected':'' ?>><?= h($s) ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn primary" type="submit"><?= icon_svg('check') ?>套用</button>
          <a class="btn ghost" href="voyages.php">重置</a>
        </div>
      </form>

      <div style="display:flex;gap:30px;flex-wrap:wrap;font-size:13px;color:var(--muted);padding:4px 0 16px;">
        <span>航次 <strong style="color:var(--text);font-family:var(--font-serif);font-size:18px;"><?= h(count($voyages)) ?></strong> 天</span>
        <span>累計人次 <strong style="color:var(--text);font-family:var(--font-serif);font-size:18px;"><?= h($total_crew) ?></strong></span>
        <span>累計時數 <strong style="color:var(--text);font-family:var(--font-serif);font-size:18px;"><?= h(round($total_hours,1)) ?></strong> hr</span>
      </div>

      <?php if (!$voyages): ?>
        <div class="empty-state" style="margin:16px 0 0;">
          <h3>無航次紀錄</h3>
          <p>選定期間內沒有任何值勤記錄。請調整日期範圍或篩選條件。</p>
        </div>
      <?php else: ?>
        <div class="voy-list">
          <?php foreach ($voyages as $v):
            $zones = $v['zones'] ? explode(',', $v['zones']) : [];
            $seas  = $v['seas']  ? explode(',', $v['seas'])  : [];
            $vessels = $v['vessels'] ? explode(',', $v['vessels']) : [];
            $hrs = $v['total_mins'] ? round($v['total_mins']/60, 1) : 0;
            $wdn = $wd_zh[(int)date('w', strtotime($v['work_date']))];
          ?>
            <div class="voy-row">
              <div class="voy-date">
                <?= h(date('m/d', strtotime($v['work_date']))) ?>
                <span class="voy-wd"><?= h(date('Y', strtotime($v['work_date']))) ?> · 星期<?= h($wdn) ?></span>
              </div>
              <div class="voy-meta">
                <span class="voy-stat">人員 <strong style="color:var(--text);"><?= h($v['crew_count']) ?></strong></span>
                <span class="voy-stat">時數 <strong style="color:var(--text);"><?= h($hrs) ?></strong> hr</span>
                <span class="voy-stat">已下勤 <strong style="color:var(--text);"><?= h($v['done_count']) ?></strong></span>
                <?php if ($vessels): ?>
                  <span class="voy-stat">艦號 <strong style="color:var(--text);"><?= h(implode(' / ', $vessels)) ?></strong></span>
                <?php endif; ?>
                <div class="voy-chips">
                  <?php foreach ($zones as $z): ?>
                    <span class="cond-chip <?= h($zone_cls[$z] ?? '') ?>"><span class="cond-k">海域</span><?= h($z) ?></span>
                  <?php endforeach; ?>
                  <?php foreach ($seas as $s): ?>
                    <span class="cond-chip <?= h($sea_cls[$s] ?? '') ?>"><span class="cond-k">海象</span><?= h($s) ?></span>
                  <?php endforeach; ?>
                </div>
              </div>
              <div class="voy-count">
                <?= h($v['crew_count']) ?>
                <small>人次出勤</small>
              </div>
            </div>
          <?php endforeach; ?>
        </div>
      <?php endif; ?>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
