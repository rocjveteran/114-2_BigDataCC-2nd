<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

date_default_timezone_set('Asia/Taipei');

$uid   = (int)$_SESSION['user_id'];
$today = date('Y-m-d');
$wd_zh = ['日','一','二','三','四','五','六'];
$wd    = $wd_zh[(int)date('w')];

// ── 今日打卡 ────────────────────────────────────────────────────────────────
$stmt = $pdo->prepare("SELECT check_in, check_out, duty_zone, sea_state FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
$stmt->execute([$uid, $today]);
$today_att = $stmt->fetch();

// ── 今日請假 ────────────────────────────────────────────────────────────────
$stmt = $pdo->prepare("SELECT leave_type FROM leaves WHERE user_id=? AND status='approved' AND date_from<=? AND date_to>=? LIMIT 1");
$stmt->execute([$uid, $today, $today]);
$today_leave = $stmt->fetchColumn();

// ── 本週時數 ────────────────────────────────────────────────────────────────
$dow      = (int)date('N');
$wk_start = date('Y-m-d', strtotime("-".($dow-1)." days"));
$wk_end   = date('Y-m-d', strtotime("+".(7-$dow)." days"));
$stmt = $pdo->prepare("SELECT SUM(TIMESTAMPDIFF(MINUTE,check_in,check_out)) AS mins, COUNT(*) AS days
                       FROM attendance WHERE user_id=? AND work_date BETWEEN ? AND ?
                         AND check_in IS NOT NULL AND check_out IS NOT NULL");
$stmt->execute([$uid, $wk_start, $wk_end]);
$wk = $stmt->fetch();
$wk_hours = $wk['mins'] ? round($wk['mins']/60, 1) : 0;
$wk_days  = (int)($wk['days'] ?? 0);

// ── 本月時數 ────────────────────────────────────────────────────────────────
$mo_start = date('Y-m-01');
$mo_end   = date('Y-m-t');
$stmt = $pdo->prepare("SELECT SUM(TIMESTAMPDIFF(MINUTE,check_in,check_out)) AS mins, COUNT(*) AS days
                       FROM attendance WHERE user_id=? AND work_date BETWEEN ? AND ?
                         AND check_in IS NOT NULL AND check_out IS NOT NULL");
$stmt->execute([$uid, $mo_start, $mo_end]);
$mo = $stmt->fetch();
$mo_hours = $mo['mins'] ? round($mo['mins']/60, 1) : 0;
$mo_days  = (int)($mo['days'] ?? 0);

// ── 本月個人暴露統計 ─────────────────────────────────────────────────────────
$stmt = $pdo->prepare("SELECT
    COUNT(*) as total,
    SUM(CASE WHEN duty_zone='外海' THEN 1 ELSE 0 END) as offshore_cnt,
    SUM(CASE WHEN sea_state IN ('中浪','大浪') THEN 1 ELSE 0 END) as rough_cnt,
    SUM(CASE WHEN sea_state='大浪' THEN 1 ELSE 0 END) as storm_cnt
  FROM attendance WHERE user_id=? AND work_date BETWEEN ? AND ?
    AND duty_zone IS NOT NULL AND check_out IS NOT NULL");
$stmt->execute([$uid, $mo_start, $mo_end]);
$expo = $stmt->fetch();
$expo_total      = (int)($expo['total'] ?? 0);
$offshore_pct    = $expo_total > 0 ? (int)round($expo['offshore_cnt'] / $expo_total * 100) : 0;
$rough_pct       = $expo_total > 0 ? (int)round($expo['rough_cnt']    / $expo_total * 100) : 0;
$storm_pct       = $expo_total > 0 ? (int)round($expo['storm_cnt']    / $expo_total * 100) : 0;
$risk_score      = (int)round($offshore_pct * 0.55 + $rough_pct * 0.45);
$risk_level      = $risk_score >= 40 ? 'high' : ($risk_score >= 20 ? 'mid' : 'low');
$risk_label      = ['low'=>'低','mid'=>'中','high'=>'高'][$risk_level];
$risk_color      = ['low'=>'var(--ok)','mid'=>'var(--warn)','high'=>'var(--accent)'][$risk_level];

// ── 近 5 筆值勤記錄 ──────────────────────────────────────────────────────────
$stmt = $pdo->prepare("SELECT work_date, duty_zone, sea_state,
    TIMESTAMPDIFF(MINUTE,check_in,check_out) AS mins
  FROM attendance WHERE user_id=? AND check_out IS NOT NULL
  ORDER BY work_date DESC LIMIT 5");
$stmt->execute([$uid]);
$recent_duties = $stmt->fetchAll();

// ── 待批請假（自己） ─────────────────────────────────────────────────────────
$stmt = $pdo->prepare("SELECT COUNT(*) FROM leaves WHERE user_id=? AND status='pending'");
$stmt->execute([$uid]);
$pending = (int)$stmt->fetchColumn();

// ── 近 14 天 sparkline ──────────────────────────────────────────────────────
$stmt = $pdo->prepare("SELECT work_date, TIMESTAMPDIFF(MINUTE,check_in,check_out) AS mins
                       FROM attendance WHERE user_id=? AND work_date >= ?
                         AND check_in IS NOT NULL AND check_out IS NOT NULL
                       ORDER BY work_date ASC");
$stmt->execute([$uid, date('Y-m-d', strtotime('-13 days'))]);
$rows = $stmt->fetchAll();
$by_date = [];
foreach ($rows as $r) $by_date[$r['work_date']] = round(((int)$r['mins'])/60, 1);
$spark = [];
for ($i=13; $i>=0; $i--) {
  $d       = date('Y-m-d', strtotime("-{$i} days"));
  $spark[] = ['d'=>$d, 'h'=>$by_date[$d] ?? 0];
}
$max_h = max(array_column($spark, 'h')) ?: 1;

// ── 艦上今日配置 ─────────────────────────────────────────────────────────────
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
  if ($cr['lv_type'])                                    $cnt_leave++;
  elseif (!empty($cr['check_in']) && empty($cr['check_out'])) $cnt_on++;
  elseif (!empty($cr['check_out']))                      $cnt_done++;
  else                                                   $cnt_off++;
}
$crew_total = count($crew_all);

// ── 今日主要海況（統計 DB） ──────────────────────────────────────────────────
$stmt = $pdo->prepare("SELECT duty_zone FROM attendance WHERE work_date=? AND duty_zone IS NOT NULL GROUP BY duty_zone ORDER BY COUNT(*) DESC LIMIT 1");
$stmt->execute([$today]);
$today_zone = $stmt->fetchColumn() ?: ($_SESSION['today_zone'] ?? null);
$stmt = $pdo->prepare("SELECT sea_state FROM attendance WHERE work_date=? AND sea_state IS NOT NULL GROUP BY sea_state ORDER BY COUNT(*) DESC LIMIT 1");
$stmt->execute([$today]);
$today_sea = $stmt->fetchColumn() ?: ($_SESSION['today_sea'] ?? null);

// ── 讀取決策警示（recommendations.json） ────────────────────────────────────
$rec_alerts = [];
$rec_rotation = [];
$rec_markov = null;
$rec_sea_now = null;
$rec_ml_tomorrow = null;
$my_fatigue = null;
$output_dir = getenv('OUTPUT_DIR') ?: '/app/output';
$rec_path   = $output_dir . '/recommendations.json';
// Fallback：本機開發時 OUTPUT_DIR 未設則讀 app 內 analysis_output
if (!file_exists($rec_path) && file_exists(__DIR__ . '/analysis_output/recommendations.json')) {
  $rec_path = __DIR__ . '/analysis_output/recommendations.json';
}
if (file_exists($rec_path)) {
  $rec_raw = @json_decode(file_get_contents($rec_path), true);
  if ($rec_raw) {
    $rec_alerts   = array_values(array_filter($rec_raw['alerts'] ?? [], fn($a) => in_array($a['level'], ['warn','err'])));
    $rec_rotation = array_values(array_filter($rec_raw['rotation_suggestions'] ?? [], fn($r) => $r['priority'] === 'high'));
    $rec_markov   = $rec_raw['markov_rough_7day'] ?? null;
    $rec_sea_now  = $rec_raw['sea_now'] ?? null;
    $rec_ml_tomorrow = $rec_raw['ml_rough_tomorrow'] ?? null;
    foreach (($rec_raw['fatigue'] ?? []) as $f) {
      if ((int)($f['user_id'] ?? 0) === $uid) { $my_fatigue = $f; break; }
    }
  }
}

// ── 今日狀態 ────────────────────────────────────────────────────────────────
if ($today_leave)
  $today_status = ['請假中','warn'];
elseif (!empty($today_att['check_in']) && empty($today_att['check_out']))
  $today_status = ['值勤中','info'];
elseif (!empty($today_att['check_out']))
  $today_status = ['今日已結束','ok'];
else
  $today_status = ['尚未打卡','off'];

// ── Sparkline 幾何 ──────────────────────────────────────────────────────────
$w = 280; $hgt = 56; $padL = 6; $padR = 6; $padT = 4; $padB = 12;
$inner_w = $w - $padL - $padR; $inner_h = $hgt - $padT - $padB;
$n = count($spark); $step = $inner_w / max($n-1, 1);
$pts = [];
foreach ($spark as $i => $p) {
  $x = $padL + $i * $step;
  $y = $padT + $inner_h - ($p['h'] / $max_h) * $inner_h;
  $pts[] = [$x, $y, $p];
}
$polyline = implode(' ', array_map(fn($p) => round($p[0],1).','.round($p[1],1), $pts));
$area = "M ".round($pts[0][0],1)." ".round($padT+$inner_h,1)
      . " L ".implode(' L ', array_map(fn($p) => round($p[0],1).' '.round($p[1],1), $pts))
      . " L ".round(end($pts)[0],1)." ".round($padT+$inner_h,1)." Z";

// ── 海況橫幅設定（今日值勤海況優先，否則退回 CWA 浮標即時觀測）────────────────
$banner_sea    = $today_sea ?: ($rec_sea_now['sea_state'] ?? null);
$sea_from_buoy = !$today_sea && $banner_sea;
$sea_level_map = ['平靜'=>0,'輕浪'=>1,'中浪'=>2,'大浪'=>3];
$sea_level     = $sea_level_map[$banner_sea] ?? -1;
$banner_cls    = ['calm','light','med','rough'][$sea_level] ?? '';
$ops_msg       = [
  '平靜' => '海況良好，正常作業',
  '輕浪' => '輕微湧浪，可正常作業',
  '中浪' => '外海注意，評估必要時縮短任務',
  '大浪' => '⚠ 惡劣海況，外海人員請提高警覺',
][$banner_sea] ?? '暫無海況資料';
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>儀表板 · 海象感知智慧排班與勤務決策平台</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap">
    <?php
    page_header(
      '歡迎回來，'.($_SESSION['full_name'] ?? ''),
      $today.' · 星期'.$wd,
      'DASHBOARD · 儀表板'
    );
    ?>

    <?php if ($banner_sea): ?>
    <div class="sea-banner <?= h($banner_cls) ?>">
      <div class="sb-ico"><?= icon_svg('wave') ?></div>
      <div class="sb-body">
        <div class="sb-title"><?= $sea_from_buoy ? '即時海象（CWA 浮標觀測）' : '今日海象狀態' ?></div>
        <div class="sb-chips">
          <?php if ($today_zone): $zm = ['港口'=>'zone-port','近海'=>'zone-near','外海'=>'zone-far']; ?>
            <span class="sb-badge cond-chip <?= h($zm[$today_zone] ?? '') ?>">
              <?= icon_svg('anchor') ?> <?= h($today_zone) ?>
            </span>
          <?php endif; ?>
          <?php $sm = ['平靜'=>'sea-calm','輕浪'=>'sea-light','中浪'=>'sea-med','大浪'=>'sea-rough']; ?>
          <span class="sb-badge cond-chip <?= h($sm[$banner_sea] ?? '') ?>">
            <?= icon_svg('wave') ?> <?= h($banner_sea) ?>
          </span>
          <?php if ($rec_ml_tomorrow !== null): ?>
          <span class="sb-badge">🤖 ML 明日惡劣海況 <?= h($rec_ml_tomorrow) ?>%</span>
          <?php endif; ?>
          <?php if ($rec_markov !== null): ?>
          <span class="sb-badge">📡 Markov 7天大浪 <?= h($rec_markov) ?>%</span>
          <?php endif; ?>
          <?php if ($rec_sea_now && $rec_sea_now['wave_height'] !== null): ?>
          <span class="sb-badge">🌊 浮標波高 <?= h($rec_sea_now['wave_height']) ?>m</span>
          <?php endif; ?>
        </div>
      </div>
      <span class="sb-ops"><?= h($ops_msg) ?></span>
    </div>
    <?php endif; ?>

    <?php if ($rec_alerts || $rec_rotation): ?>
    <div class="dash-alert-strip">
      <?php foreach ($rec_alerts as $al): ?>
      <div class="das-item <?= h($al['level']) ?>">
        <span class="das-ico"><?= icon_svg($al['level']==='err'?'x':'wave') ?></span>
        <span><?= h($al['text']) ?></span>
      </div>
      <?php endforeach; ?>
      <?php foreach ($rec_rotation as $r): ?>
      <div class="das-item warn">
        <span class="das-ico"><?= icon_svg('users') ?></span>
        <span><strong><?= h($r['name']) ?></strong>　<?= h($r['action']) ?>（外海 <?= h($r['offshore_pct']) ?>%，大浪 <?= h($r['rough_sea_pct']) ?>%）</span>
      </div>
      <?php endforeach; ?>
    </div>
    <?php endif; ?>

    <div class="stat-grid">
      <?php
        $st_card_cls = match($today_status[1]) {
          'info' => 'accent', 'ok' => 'ok', 'warn' => 'warn', default => ''
        };
      ?>
      <div class="stat-card <?= h($st_card_cls) ?>">
        <div class="stat-icon"><?= icon_svg('clock') ?></div>
        <div class="stat-lbl">今日狀態</div>
        <div class="stat-num"><?= h($today_status[0]) ?></div>
        <?php if (!empty($today_att['check_in'])): ?>
          <div class="stat-sub">開始 <?= h(substr($today_att['check_in'],11,5)) ?><?= !empty($today_att['check_out']) ? ' · 結束 '.h(substr($today_att['check_out'],11,5)) : '' ?></div>
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

      <div class="stat-card <?= $risk_level==='high'?'accent':($risk_level==='mid'?'warn':'') ?>">
        <div class="stat-icon" style="color:<?= $risk_color ?>;background:color-mix(in srgb,<?= $risk_color ?> 12%,transparent);"><?= icon_svg('shield') ?></div>
        <div class="stat-lbl">本月風險積分</div>
        <div class="stat-num" style="color:<?= $risk_color ?>;"><?= h($risk_score) ?><span style="font-size:16px;color:var(--muted);font-family:var(--font-sans);">&nbsp;/ 100</span></div>
        <div class="stat-sub">外海 <?= h($offshore_pct) ?>% · 大浪 <?= h($storm_pct) ?>% · 風險<?= h($risk_label) ?></div>
      </div>
    </div>

    <div class="exposure-row">
      <div class="expo-card">
        <div class="expo-label">外海值勤比例（本月）</div>
        <div class="expo-pct"><?= h($offshore_pct) ?><span>%</span></div>
        <div class="expo-bar"><div class="expo-bar-fill <?= $offshore_pct>=50?'high':($offshore_pct>=30?'mid':'low') ?>" style="width:<?= min($offshore_pct,100) ?>%;"></div></div>
      </div>
      <div class="expo-card">
        <div class="expo-label">惡劣海況值勤比例（中浪以上）</div>
        <div class="expo-pct"><?= h($rough_pct) ?><span>%</span></div>
        <div class="expo-bar"><div class="expo-bar-fill <?= $rough_pct>=30?'high':($rough_pct>=15?'mid':'low') ?>" style="width:<?= min($rough_pct,100) ?>%;"></div></div>
      </div>
      <div class="expo-card">
        <div class="expo-label">大浪值勤比例（本月）</div>
        <div class="expo-pct"><?= h($storm_pct) ?><span>%</span></div>
        <div class="expo-bar"><div class="expo-bar-fill <?= $storm_pct>=20?'high':($storm_pct>=10?'mid':'low') ?>" style="width:<?= min($storm_pct,100) ?>%;"></div></div>
      </div>
      <?php if ($my_fatigue !== null):
        $fscore = (int)$my_fatigue['fatigue_score'];
        $flvl = $fscore >= 65 ? 'high' : ($fscore >= 40 ? 'mid' : 'low');
        $flbl = ['low'=>'良好','mid'=>'適中','high'=>'偏高'][$flvl];
      ?>
      <div class="expo-card">
        <div class="expo-label">疲勞指數（連續值勤 <?= h($my_fatigue['consecutive_days']) ?> 天）</div>
        <div class="expo-pct"><?= h($fscore) ?><span> / 100 · <?= h($flbl) ?></span></div>
        <div class="expo-bar"><div class="expo-bar-fill <?= $flvl ?>" style="width:<?= min($fscore,100) ?>%;"></div></div>
      </div>
      <?php else: ?>
      <div class="expo-card">
        <div class="expo-label">本月待批請假</div>
        <div class="expo-pct" style="color:<?= $pending>0?'var(--warn)':'var(--ok)' ?>;"><?= h($pending) ?><span> 筆</span></div>
        <div class="expo-bar"><div class="expo-bar-fill <?= $pending>2?'high':($pending>0?'mid':'low') ?>" style="width:<?= min($pending*25,100) ?>%;"></div></div>
      </div>
      <?php endif; ?>
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

        <?php if ($recent_duties): ?>
        <div style="margin-top:14px;">
          <div style="font-size:12px;color:var(--muted);margin-bottom:6px;font-weight:500;letter-spacing:.3px;">近期值勤記錄</div>
          <ul class="recent-duties">
            <?php
            $z_cls = ['港口'=>'sea-calm','近海'=>'sea-light','外海'=>'sea-rough'];
            $s_cls = ['平靜'=>'sea-calm','輕浪'=>'sea-light','中浪'=>'sea-med','大浪'=>'sea-rough'];
            foreach ($recent_duties as $rd):
              $hrs = $rd['mins'] ? round($rd['mins']/60, 1) : '—';
            ?>
            <li>
              <span class="rd-date"><?= h(date('m/d', strtotime($rd['work_date']))) ?></span>
              <?php if ($rd['duty_zone']): ?>
                <span class="rd-zone cond-chip <?= h($z_cls[$rd['duty_zone']] ?? '') ?>" style="font-size:11.5px;padding:2px 7px;"><?= h($rd['duty_zone']) ?></span>
              <?php endif; ?>
              <?php if ($rd['sea_state']): ?>
                <span class="rd-sea cond-chip <?= h($s_cls[$rd['sea_state']] ?? '') ?>" style="font-size:11.5px;padding:2px 7px;"><?= h($rd['sea_state']) ?></span>
              <?php endif; ?>
              <span class="rd-hrs"><?= h($hrs) ?> hr</span>
            </li>
            <?php endforeach; ?>
          </ul>
        </div>
        <?php endif; ?>
      </div>

      <div class="card">
        <div class="card-head">
          <h2>今日艦上配置</h2>
          <span class="live-badge"><span class="live-dot"></span>即時 · <span id="js-ts"><?= h(date('H:i:s')) ?></span></span>
        </div>
        <div style="display:flex;align-items:center;gap:18px;padding:8px 0;">
          <div style="flex:1;">
            <div style="font-family:var(--font-serif);font-size:40px;color:var(--text);line-height:1;letter-spacing:-0.6px;"><span id="js-onduty"><?= h($cnt_on + $cnt_done) ?></span>
              <span style="font-size:18px;color:var(--muted);font-family:var(--font-sans);">/ <?= h($crew_total) ?></span>
            </div>
            <div style="font-size:12.5px;color:var(--muted);margin-top:4px;">人員出勤（含已下勤）</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:6px;font-size:13px;">
            <div style="display:flex;align-items:center;gap:8px;"><span class="ship-legend-dot on"></span>值勤中 <strong id="js-on"><?= h($cnt_on) ?></strong></div>
            <div style="display:flex;align-items:center;gap:8px;"><span class="ship-legend-dot done"></span>已結束 <strong id="js-done"><?= h($cnt_done) ?></strong></div>
            <div style="display:flex;align-items:center;gap:8px;"><span class="ship-legend-dot leave"></span>請假 <strong id="js-leave"><?= h($cnt_leave) ?></strong></div>
            <div style="display:flex;align-items:center;gap:8px;"><span class="ship-legend-dot off"></span>未值勤 <strong id="js-off"><?= h($cnt_off) ?></strong></div>
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px;">
          <a class="btn small" href="punch.php"><?= icon_svg('ship') ?>前往打卡</a>
          <a class="btn small" href="crew.php"><?= icon_svg('users') ?>人員配置</a>
        </div>

        <?php if (is_admin() && $rec_rotation): ?>
        <div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--line);">
          <div style="font-size:12px;color:var(--muted);margin-bottom:8px;font-weight:500;letter-spacing:.3px;">輪換建議</div>
          <?php foreach ($rec_rotation as $r): ?>
          <div style="display:flex;align-items:center;justify-content:space-between;padding:5px 0;font-size:12.5px;border-bottom:1px solid var(--line);">
            <span style="font-weight:500;"><?= h($r['name']) ?></span>
            <span style="color:var(--accent);font-size:11.5px;"><?= h($r['action']) ?></span>
          </div>
          <?php endforeach; ?>
        </div>
        <?php endif; ?>
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
  <script>
  // 即時艦上狀態：每 60 秒輪詢 api_status.php 自動刷新「今日艦上配置」
  (function () {
    var set = function (id, v) { var el = document.getElementById(id); if (el && v != null) el.textContent = v; };
    function refresh() {
      fetch('api_status.php', { credentials: 'same-origin', cache: 'no-store' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (!d || !d.crew) return;
          set('js-on', d.crew.on); set('js-done', d.crew.done);
          set('js-leave', d.crew.leave); set('js-off', d.crew.off);
          set('js-onduty', d.on_duty); set('js-ts', d.ts);
        })
        .catch(function () { /* 靜默失敗，下次再試 */ });
    }
    setInterval(refresh, 60000);
  })();
  </script>
</body>
</html>
