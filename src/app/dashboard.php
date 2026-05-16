<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

date_default_timezone_set('Asia/Taipei');

$uid = (int)$_SESSION['user_id'];
$today = date('Y-m-d');
$wd_zh = ['日','一','二','三','四','五','六'];
$wd = $wd_zh[(int)date('w')];

// Today's punch
$stmt = $pdo->prepare("SELECT check_in, check_out, duty_zone, sea_state FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
$stmt->execute([$uid, $today]);
$today_att = $stmt->fetch();

// Today's leave?
$stmt = $pdo->prepare("SELECT leave_type FROM leaves WHERE user_id=? AND status='approved' AND date_from<=? AND date_to>=? LIMIT 1");
$stmt->execute([$uid, $today, $today]);
$today_leave = $stmt->fetchColumn();

// This week hours (Mon-Sun)
$dow = (int)date('N'); // 1=Mon...7=Sun
$wk_start = date('Y-m-d', strtotime("-".($dow-1)." days"));
$wk_end   = date('Y-m-d', strtotime("+".(7-$dow)." days"));
$stmt = $pdo->prepare("SELECT SUM(TIMESTAMPDIFF(MINUTE, check_in, check_out)) AS mins, COUNT(*) AS days
                       FROM attendance WHERE user_id=? AND work_date BETWEEN ? AND ?
                         AND check_in IS NOT NULL AND check_out IS NOT NULL");
$stmt->execute([$uid, $wk_start, $wk_end]);
$wk = $stmt->fetch();
$wk_hours = $wk['mins'] ? round($wk['mins']/60, 1) : 0;
$wk_days  = (int)($wk['days'] ?? 0);

// This month
$mo_start = date('Y-m-01');
$mo_end   = date('Y-m-t');
$stmt = $pdo->prepare("SELECT SUM(TIMESTAMPDIFF(MINUTE, check_in, check_out)) AS mins, COUNT(*) AS days
                       FROM attendance WHERE user_id=? AND work_date BETWEEN ? AND ?
                         AND check_in IS NOT NULL AND check_out IS NOT NULL");
$stmt->execute([$uid, $mo_start, $mo_end]);
$mo = $stmt->fetch();
$mo_hours = $mo['mins'] ? round($mo['mins']/60, 1) : 0;
$mo_days  = (int)($mo['days'] ?? 0);

// Pending leaves (own)
$stmt = $pdo->prepare("SELECT COUNT(*) FROM leaves WHERE user_id=? AND status='pending'");
$stmt->execute([$uid]);
$pending = (int)$stmt->fetchColumn();

// Last 14 days sparkline data
$stmt = $pdo->prepare("SELECT work_date, TIMESTAMPDIFF(MINUTE, check_in, check_out) AS mins
                       FROM attendance WHERE user_id=? AND work_date >= ?
                         AND check_in IS NOT NULL AND check_out IS NOT NULL
                       ORDER BY work_date ASC");
$stmt->execute([$uid, date('Y-m-d', strtotime('-13 days'))]);
$rows = $stmt->fetchAll();
$by_date = [];
foreach ($rows as $r) $by_date[$r['work_date']] = round(((int)$r['mins'])/60, 1);
$spark = [];
for ($i=13; $i>=0; $i--) {
  $d = date('Y-m-d', strtotime("-{$i} days"));
  $spark[] = ['d' => $d, 'h' => $by_date[$d] ?? 0];
}
$max_h = max(array_column($spark, 'h')) ?: 1;

// Ship-wide today: count by status
$stmt = $pdo->prepare("
  SELECT u.user_id, u.full_name,
         a.check_in, a.check_out,
         (SELECT leave_type FROM leaves lv WHERE lv.user_id=u.user_id AND lv.status='approved'
            AND lv.date_from<=? AND lv.date_to>=? LIMIT 1) AS lv_type
  FROM users u
  LEFT JOIN attendance a ON a.user_id=u.user_id AND a.work_date=?
  WHERE u.is_active=1");
$stmt->execute([$today, $today, $today]);
$crew_all = $stmt->fetchAll();
$cnt_on = 0; $cnt_done = 0; $cnt_leave = 0; $cnt_off = 0;
foreach ($crew_all as $cr) {
  if ($cr['lv_type']) $cnt_leave++;
  elseif (!empty($cr['check_in']) && empty($cr['check_out'])) $cnt_on++;
  elseif (!empty($cr['check_out'])) $cnt_done++;
  else $cnt_off++;
}
$crew_total = count($crew_all);

// Today's ship conditions (DB mode → session fallback)
$today_zone = null; $today_sea = null;
$stmt = $pdo->prepare("SELECT duty_zone FROM attendance WHERE work_date=? AND duty_zone IS NOT NULL GROUP BY duty_zone ORDER BY COUNT(*) DESC LIMIT 1");
$stmt->execute([$today]);
$today_zone = $stmt->fetchColumn() ?: null;
$stmt = $pdo->prepare("SELECT sea_state FROM attendance WHERE work_date=? AND sea_state IS NOT NULL GROUP BY sea_state ORDER BY COUNT(*) DESC LIMIT 1");
$stmt->execute([$today]);
$today_sea = $stmt->fetchColumn() ?: null;
if (!$today_zone) $today_zone = $_SESSION['today_zone'] ?? null;
if (!$today_sea)  $today_sea  = $_SESSION['today_sea']  ?? null;

// Today status label
if ($today_leave)                                                $today_status = ['請假中','warn'];
elseif (!empty($today_att['check_in']) && empty($today_att['check_out'])) $today_status = ['值勤中','info'];
elseif (!empty($today_att['check_out']))                         $today_status = ['今日已結束','ok'];
else                                                             $today_status = ['尚未打卡','off'];

// Sparkline geometry
$w = 280; $hgt = 56; $padL = 6; $padR = 6; $padT = 4; $padB = 12;
$inner_w = $w - $padL - $padR;
$inner_h = $hgt - $padT - $padB;
$n = count($spark);
$step = $inner_w / max($n-1, 1);
$pts = [];
foreach ($spark as $i => $p) {
  $x = $padL + $i * $step;
  $y = $padT + $inner_h - ($p['h'] / $max_h) * $inner_h;
  $pts[] = [$x, $y, $p];
}
$polyline = implode(' ', array_map(fn($p)=>round($p[0],1).','.round($p[1],1), $pts));
$area = "M ".round($pts[0][0],1)." ".round($padT+$inner_h,1)." L ".implode(' L ', array_map(fn($p)=>round($p[0],1).' '.round($p[1],1), $pts))." L ".round(end($pts)[0],1)." ".round($padT+$inner_h,1)." Z";
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>儀表板 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php
    $hello = $_SESSION['full_name'] ?? '';
    page_header(
      '歡迎回來，'.$hello,
      $today.' · 星期'.$wd.'。一目了然今日值勤、本週時數、艦上人員配置。',
      'DASHBOARD · 儀表板'
    );
    ?>

    <div class="stat-grid">
      <?php
        $st_card_cls = match($today_status[1]) {
          'info' => 'accent',
          'ok'   => 'ok',
          'warn' => 'warn',
          default => ''
        };
      ?>
      <div class="stat-card <?= h($st_card_cls) ?>">
        <div class="stat-icon"><?= icon_svg('clock') ?></div>
        <div class="stat-lbl">今日狀態</div>
        <div class="stat-num"><?= h($today_status[0]) ?></div>
        <?php if (!empty($today_att['check_in'])): ?>
          <div class="stat-sub">開始 <?= h(substr($today_att['check_in'], 11, 5)) ?><?= !empty($today_att['check_out']) ? ' · 結束 '.h(substr($today_att['check_out'], 11, 5)) : '' ?></div>
        <?php else: ?>
          <div class="stat-sub"><a href="punch.php" style="color:var(--primary);">→ 前往打卡</a></div>
        <?php endif; ?>
      </div>

      <div class="stat-card">
        <div class="stat-icon"><?= icon_svg('chart') ?></div>
        <div class="stat-lbl">本週累計</div>
        <div class="stat-num"><?= h($wk_hours) ?><span style="font-size:16px;color:var(--muted);font-family:var(--font-sans);">&nbsp;hr</span></div>
        <div class="stat-sub">值勤 <?= h($wk_days) ?> 天 · 週 <?= h(date('W')) ?></div>
      </div>

      <div class="stat-card">
        <div class="stat-icon"><?= icon_svg('calendar') ?></div>
        <div class="stat-lbl">本月累計</div>
        <div class="stat-num"><?= h($mo_hours) ?><span style="font-size:16px;color:var(--muted);font-family:var(--font-sans);">&nbsp;hr</span></div>
        <div class="stat-sub">值勤 <?= h($mo_days) ?> 天 · <?= h(date('Y 年 n 月')) ?></div>
      </div>

      <div class="stat-card <?= $pending>0?'accent':'' ?>">
        <div class="stat-icon"><?= icon_svg('plane') ?></div>
        <div class="stat-lbl">待批請假</div>
        <div class="stat-num"><?= h($pending) ?></div>
        <div class="stat-sub"><?= $pending>0?'有 '.$pending.' 筆請假待管理者審核':'目前沒有待批請假' ?></div>
      </div>
    </div>

    <div class="grid2">
      <div class="card">
        <div class="card-head">
          <h2>近 14 天值勤時數</h2>
          <span class="muted" style="font-size:12.5px;">最高 <?= h($max_h) ?> hr</span>
        </div>
        <div class="sparkline-wrap">
          <svg class="sparkline" viewBox="0 0 <?= $w ?> <?= $hgt ?>" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
            <path class="spk-area" d="<?= h($area) ?>"/>
            <polyline class="spk-line" points="<?= h($polyline) ?>"/>
            <?php foreach ($pts as $i => $p): $isLast = ($i === count($pts)-1); ?>
              <?php if ($p[2]['h'] > 0 || $isLast): ?>
                <circle class="spk-dot <?= $isLast?'last':'' ?>" cx="<?= round($p[0],1) ?>" cy="<?= round($p[1],1) ?>" r="<?= $isLast?2.5:1.6 ?>"/>
              <?php endif; ?>
            <?php endforeach; ?>
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:4px;">
            <span><?= h(date('m/d', strtotime($spark[0]['d']))) ?></span>
            <span><?= h(date('m/d', strtotime(end($spark)['d']))) ?></span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-head">
          <h2>今日艦上配置</h2>
          <div class="ship-conditions">
            <?php if ($today_zone): $zm = ['港口'=>'zone-port','近海'=>'zone-near','外海'=>'zone-far']; ?>
              <span class="cond-chip <?= h($zm[$today_zone] ?? '') ?>"><span class="cond-k">海域</span><?= h($today_zone) ?></span>
            <?php endif; ?>
            <?php if ($today_sea): $sm = ['平靜'=>'sea-calm','輕浪'=>'sea-light','中浪'=>'sea-med','大浪'=>'sea-rough']; ?>
              <span class="cond-chip <?= h($sm[$today_sea] ?? '') ?>"><span class="cond-k">海象</span><?= h($today_sea) ?></span>
            <?php endif; ?>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:18px;padding:8px 0;">
          <div style="flex:1;">
            <div style="font-family:var(--font-serif);font-size:40px;color:var(--text);line-height:1;letter-spacing:-0.6px;"><?= h($cnt_on + $cnt_done) ?>
              <span style="font-size:18px;color:var(--muted);font-family:var(--font-sans);">/ <?= h($crew_total) ?></span>
            </div>
            <div style="font-size:12.5px;color:var(--muted);margin-top:4px;">人員出勤（含已下勤）</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;font-size:13px;">
            <div style="display:flex;align-items:center;gap:8px;"><span class="ship-legend-dot on"></span>值勤中 <strong style="color:var(--text);"><?= h($cnt_on) ?></strong></div>
            <div style="display:flex;align-items:center;gap:8px;"><span class="ship-legend-dot done"></span>已結束 <strong style="color:var(--text);"><?= h($cnt_done) ?></strong></div>
            <div style="display:flex;align-items:center;gap:8px;"><span class="ship-legend-dot leave"></span>請假 <strong style="color:var(--text);"><?= h($cnt_leave) ?></strong></div>
            <div style="display:flex;align-items:center;gap:8px;"><span class="ship-legend-dot off"></span>未值勤 <strong style="color:var(--text);"><?= h($cnt_off) ?></strong></div>
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px;">
          <a class="btn small" href="punch.php"><?= icon_svg('ship') ?>前往打卡</a>
          <a class="btn small" href="crew.php"><?= icon_svg('users') ?>人員配置</a>
        </div>
      </div>
    </div>

    <h3 style="font-family:var(--font-serif);font-size:22px;font-weight:400;color:var(--text);margin:32px 0 14px;letter-spacing:-0.3px;">快速導航</h3>
    <div class="tile-grid">
      <a class="tile" href="punch.php"><span class="tile-ico"><?= icon_svg('clock') ?></span><div><div class="tile-name">值勤打卡</div><div class="tile-desc">開始 / 結束今日值勤</div></div></a>
      <a class="tile" href="records.php"><span class="tile-ico"><?= icon_svg('list') ?></span><div><div class="tile-name">我的紀錄</div><div class="tile-desc">過往值勤明細</div></div></a>
      <a class="tile" href="leave.php"><span class="tile-ico"><?= icon_svg('plane') ?></span><div><div class="tile-name">請假申請</div><div class="tile-desc">新增 / 查詢請假狀態</div></div></a>
      <a class="tile" href="voyages.php"><span class="tile-ico"><?= icon_svg('compass') ?></span><div><div class="tile-name">航次紀錄</div><div class="tile-desc">依日期彙整艦務</div></div></a>
      <a class="tile" href="crew.php"><span class="tile-ico"><?= icon_svg('users') ?></span><div><div class="tile-name">艦上人員</div><div class="tile-desc">花名冊與當前狀態</div></div></a>
      <a class="tile" href="profile.php"><span class="tile-ico"><?= icon_svg('user') ?></span><div><div class="tile-name">個人檔案</div><div class="tile-desc">職務、累計、設定</div></div></a>
    </div>
  </div>
  <?php page_footer(); ?>
</body>
</html>
