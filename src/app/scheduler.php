<?php
require_once 'auth.php';
require_once 'admin_only.php';
require_once 'ui.php';

// 讀取決策引擎輸出（analysis_output/recommendations.json）
$chart_dir = __DIR__ . '/analysis_output/';
$rec = null;
foreach (['filtered_recommendations.json', 'recommendations.json'] as $rfile) {
    $rp = $chart_dir . $rfile;
    if (file_exists($rp)) { $rec = json_decode(file_get_contents($rp), true); break; }
}

$sched   = $rec['schedule']   ?? [];
$fatigue = $rec['fatigue']    ?? [];
$vessels = $rec['vessel_status'] ?? [];
$sea_now = $rec['sea_now']    ?? null;
$ml      = $rec['ml_rough_tomorrow']  ?? null;
$markov  = $rec['markov_rough_7day']  ?? null;

$zone_cls = ['港口' => 'zone-port', '近海' => 'zone-near', '外海' => 'zone-far'];
$lvl_cls  = ['low' => 'ok', 'mid' => 'warn', 'high' => 'err'];

// 依海域分組班表
$by_zone = ['港口' => [], '近海' => [], '外海' => []];
foreach (($sched['assignments'] ?? []) as $a) {
    $by_zone[$a['zone']][] = $a;
}
$rough_prob = $sched['rough_prob'] ?? ($ml ?? $markov ?? 0);
$risk_cls   = $rough_prob >= 50 ? 'err' : ($rough_prob >= 25 ? 'warn' : 'ok');
?>
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>明日值勤排班 · 海勤人力資源與作業安全決策系統</title>
  <?php style_link(); ?>
</head>
<body>
<?php nav_top(); ?>
<div class="wrap" style="padding:2.5rem 16px 3rem">

  <header class="hero">
    <div class="eyebrow">決策引擎 · Automated Scheduling</div>
    <h1 class="hero-title">明日值勤排班</h1>
    <p class="lead">
      系統綜合<strong>明日海況預測</strong>、<strong>人員疲勞指數</strong>、<strong>外海暴露輪換</strong>
      與<strong>船艦可用性</strong>四項輸入，自動產生明日值勤班表。海況惡劣時自動縮減外海員額、
      過勞人員配置港口輕負荷、維護中船艦自動排除——這是純海象視覺化系統無法產出的決策。
    </p>
  </header>

  <?php if (!$sched || empty($sched['assignments'])): ?>
    <div class="empty-state">
      <h3>尚未產生排班建議</h3>
      <p class="muted">請先於互動分析介面點擊「執行分析」，或於命令列執行：</p>
      <code>docker compose run --rm analysis python analysis.py</code>
    </div>
  <?php else: ?>

  <!-- 決策輸入摘要 -->
  <div class="sched-inputs">
    <div class="si-card <?= h($risk_cls) ?>">
      <div class="si-lbl">明日惡劣海況機率</div>
      <div class="si-val"><?= h($rough_prob) ?><span>%</span></div>
      <div class="si-sub">
        <?php if ($ml !== null): ?>ML <?= h($ml) ?>%<?php endif; ?>
        <?php if ($markov !== null): ?> · Markov 7天 <?= h($markov) ?>%<?php endif; ?>
      </div>
    </div>
    <div class="si-card">
      <div class="si-lbl">即時海況（CWA 浮標）</div>
      <div class="si-val" style="font-size:28px;"><?= h($sea_now['sea_state'] ?? '—') ?></div>
      <div class="si-sub"><?php if ($sea_now): ?>波高 <?= h($sea_now['wave_height']) ?> m · <?= h($sea_now['obs_date']) ?><?php else: ?>無觀測資料<?php endif; ?></div>
    </div>
    <div class="si-card">
      <div class="si-lbl">高疲勞人員</div>
      <?php $hf = array_filter($fatigue, fn($f) => $f['level'] === 'high'); ?>
      <div class="si-val"><?= count($hf) ?><span> 人</span></div>
      <div class="si-sub">已避開高負荷配置</div>
    </div>
    <div class="si-card">
      <div class="si-lbl">可用船艦</div>
      <?php $av = array_filter($vessels, fn($v) => $v['status'] === '可用'); ?>
      <div class="si-val"><?= count($av) ?><span> / <?= count($vessels) ?></span></div>
      <div class="si-sub"><?= count($vessels) - count($av) ?> 艘維護中</div>
    </div>
  </div>

  <!-- 明日班表（三海域欄位） -->
  <section class="dash-section">
    <div class="section-head">
      <div class="eyebrow">值勤班表 · <?= h($sched['date'] ?? '') ?></div>
      <h2 class="section-title">明日各海域人員配置</h2>
      <p class="section-desc">員額已依海況風險調整：港口 <?= h($sched['zone_slots']['港口'] ?? 0) ?> · 近海 <?= h($sched['zone_slots']['近海'] ?? 0) ?> · 外海 <?= h($sched['zone_slots']['外海'] ?? 0) ?> 人。</p>
    </div>

    <div class="decision-rules">
      <span class="dr-title">排班決策邏輯</span>
      <span class="dr-item">① 惡劣海況機率越高 → 外海員額越少</span>
      <span class="dr-item">② 外海優先派「低疲勞 + 低外海暴露」者</span>
      <span class="dr-item">③ 過勞者配置港口輕負荷</span>
      <span class="dr-item">④ 維護中船艦自動排除、每艦僅一組人員</span>
      <?php
        $eng = $sched['engine'] ?? null;
        $saving = $sched['cost_saving_pct'] ?? null;
        if ($eng === 'milp'):
      ?>
      <span class="dr-item">⑤ 整數線性規劃（MILP / HiGHS）全域最佳化<?php if ($saving !== null && $saving > 0): ?>，指派成本較貪婪基準 −<?= h($saving) ?>%<?php elseif ($saving !== null): ?>（已驗證最優性差距 0%）<?php endif; ?></span>
      <?php elseif ($eng === 'greedy'): ?>
      <span class="dr-item">⑤ 貪婪啟發式引擎（MILP 備援模式）</span>
      <?php endif; ?>
    </div>

    <?php if (!empty($sched['vessel_limited'])): ?>
    <div class="msg warn" style="margin:0 0 16px;">
      <?php foreach ($sched['vessel_limited'] as $vl): ?>
        ⚠ <?= h($vl['zone']) ?>海域可用船艦不足（需 <?= h($vl['slots']) ?> 組、僅 <?= h($vl['available_vessels']) ?> 艘可用），實際僅排 <?= h($vl['filled']) ?> 組。建議加速維護或調度其他海域船艦。
      <?php endforeach; ?>
    </div>
    <?php endif; ?>

    <div class="roster-grid">
      <?php foreach (['港口', '近海', '外海'] as $zone):
        $list = $by_zone[$zone]; ?>
      <div class="roster-col">
        <div class="roster-head <?= h($zone_cls[$zone]) ?>">
          <span><?= h($zone) ?></span>
          <span class="roster-count"><?= count($list) ?> 人</span>
        </div>
        <?php if (!$list): ?>
          <div class="roster-empty">本海域明日無配置</div>
        <?php else: foreach ($list as $a):
          $flv = $a['fatigue_score'] >= 65 ? 'err' : ($a['fatigue_score'] >= 40 ? 'warn' : 'ok'); ?>
          <div class="roster-card">
            <div class="rc-top">
              <span class="rc-name"><?= h($a['name']) ?></span>
              <span class="rc-vessel"><?= icon_svg('ship') ?> <?= h($a['vessel']) ?></span>
            </div>
            <div class="rc-meta">
              <span class="badge <?= h($flv) ?>">疲勞 <?= h($a['fatigue_score']) ?></span>
              <span class="muted" style="font-size:12px;">外海暴露 <?= h($a['offshore_pct']) ?>%</span>
            </div>
            <div class="rc-reason"><?= h($a['reason']) ?></div>
          </div>
        <?php endforeach; endif; ?>
      </div>
      <?php endforeach; ?>
    </div>
  </section>

  <div class="grid2">
    <!-- 建議輪休 -->
    <div class="card" style="padding:18px 20px;">
      <div class="card-head"><h3>建議輪休人員</h3></div>
      <?php $rest = $sched['rest_recommended'] ?? []; ?>
      <?php if (!$rest): ?>
        <p class="muted" style="font-size:13.5px;">目前無人員達輪休門檻，人力配置充足。</p>
      <?php else: foreach ($rest as $r): ?>
        <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--border);font-size:13.5px;">
          <span style="font-weight:500;"><?= h($r['name']) ?></span>
          <span class="badge err">疲勞 <?= h($r['fatigue_score']) ?></span>
        </div>
      <?php endforeach; endif; ?>
    </div>

    <!-- 船艦維護 -->
    <div class="card" style="padding:18px 20px;">
      <div class="card-head"><h3>船艦可用性</h3></div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <tr style="color:var(--muted);font-size:12px;">
          <th style="text-align:left;padding:4px 0;">船艦</th>
          <th style="text-align:left;">母港海域</th>
          <th style="text-align:right;">可用度</th>
          <th style="text-align:right;">狀態</th>
        </tr>
        <?php foreach ($vessels as $v): ?>
        <tr style="border-top:1px solid var(--border);">
          <td style="padding:6px 0;font-family:var(--font-mono);font-size:12.5px;"><?= h($v['vessel']) ?></td>
          <td><?= h($v['zone']) ?></td>
          <td style="text-align:right;"><?= h($v['availability_pct']) ?>%</td>
          <td style="text-align:right;">
            <span class="badge <?= $v['status'] === '需維護' ? 'err' : 'ok' ?>"><?= h($v['status']) ?></span>
          </td>
        </tr>
        <?php endforeach; ?>
      </table>
    </div>
  </div>

  <?php if (!empty($rec['generated_at'])): ?>
    <div class="muted" style="font-size:12.5px;margin-top:18px;">決策報告生成時間：<?= h($rec['generated_at']) ?></div>
  <?php endif; ?>

  <?php endif; ?>
</div>
<?php page_footer(); ?>
</body>
</html>
