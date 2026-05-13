<?php
require_once 'auth.php';
require_once 'admin_only.php';
require_once 'ui.php';

$chart_dir  = __DIR__ . '/analysis_output/';
$_host      = preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? 'localhost');
$gradio_url = 'http://' . $_host . ':7860';

// 章節分組：每組 = [eyebrow, 標題, 描述, [檔名 => [圖表名, 一行說明]]]
$sections = [
    [
        'eyebrow' => '時序趨勢',
        'title'   => '值勤與請假月度走勢',
        'desc'    => '從時間軸觀察整體工作量、星期效應與請假申請的波動，找出尖峰月份與淡季區間。',
        'charts'  => [
            'monthly_trend.png'   => ['月度值勤人次趨勢', '每月累計的值勤人次變化。'],
            'leave_trend.png'     => ['每月核准請假件數', '核准請假數的月度趨勢，反映人力可用度。'],
            'weekday_pattern.png' => ['週幾出勤模式', '左軸為值勤次數、右軸為平均工時，比較星期一到星期日的負載差異。'],
        ],
    ],
    [
        'eyebrow' => '任務分布',
        'title'   => '海域、海況與工時',
        'desc'    => '比較不同海域、海況條件下的值勤分布、單次時數差異與兩者交互效應。',
        'charts'  => [
            'zone_bar.png'           => ['值勤海域分布', '港口、近海、外海三類海域的值勤次數。'],
            'zone_sea_stacked.png'   => ['各海域海況分布', '每個海域在不同海況下的比例堆疊圖。'],
            'hours_boxplot.png'      => ['各海況值勤時數分布', '海況等級對單次值勤時數的影響（盒鬚圖）。'],
            'hours_heatmap.png'      => ['海域×海況平均工時', '同樣海況下，不同海域工時差多少？揭露兩個維度的交互效應。'],
            'sea_obs_comparison.png' => ['海況對照：觀測 vs 模擬', '模擬資料與中央氣象署觀測值的海況分布比對（需先執行 fetch_sea_data.py）。'],
        ],
    ],
    [
        'eyebrow' => '資源使用',
        'title'   => '船艦調度與人員出勤',
        'desc'    => '觀察各船艦使用頻率、80/20 集中度與人員月度出勤密度，輔助派遣與輪值決策。',
        'charts'  => [
            'vessel_count.png'   => ['各船艦值勤次數', '各艘船艦被派遣的累計次數排行。'],
            'vessel_pareto.png'  => ['船艦使用 Pareto', '柏拉圖（80/20 法則）：少數船艦是否扛多數工作量？'],
            'person_heatmap.png' => ['人員月度出勤熱力圖', '每位員工每月的出勤密度，紅色越深代表越頻繁。'],
        ],
    ],
    [
        'eyebrow' => '異常診斷',
        'title'   => '離群值勤偵測',
        'desc'    => '以統計方法找出可能需要覆核的異常值勤紀錄。',
        'charts'  => [
            'anomaly_detect.png' => ['異常值勤偵測（Z-score）', '紅色 X 標示工時偏離平均超過 2 個標準差的紀錄，灰色帶為 ±2σ 正常區間。'],
        ],
    ],
];

// 解析所有圖表的實際路徑（含 filtered_ 前綴 fallback）
$resolved   = [];
$latest_ts  = 0;
$has_filter = false;
foreach ($sections as $sec) {
    foreach ($sec['charts'] as $file => $_meta) {
        $path = $chart_dir . $file;
        if (!file_exists($path)) {
            $fpath = $chart_dir . 'filtered_' . $file;
            if (file_exists($fpath)) { $path = $fpath; $has_filter = true; }
            else continue;
        }
        $ts = filemtime($path);
        $resolved[$file] = ['path' => $path, 'mtime' => $ts];
        if ($ts > $latest_ts) $latest_ts = $ts;
    }
}
$total_charts = count($resolved);
$any = $total_charts > 0;

// 載入統計檢定結果（先試 filtered_，再試一般）
$stats = null;
foreach (['filtered_stats_summary.json', 'stats_summary.json'] as $sfile) {
    $sp = $chart_dir . $sfile;
    if (file_exists($sp)) {
        $stats = json_decode(file_get_contents($sp), true);
        break;
    }
}
?>
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>分析儀表板 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
<?php nav_top(); ?>
<div class="wrap" style="padding:2.5rem 16px 3rem">

  <header class="hero">
    <div class="eyebrow">資料分析 · Analysis</div>
    <h1 class="hero-title">海事勤務分析儀表板</h1>
    <p class="lead">
      以六個月實際與模擬值勤資料生成 11 張統計圖表與推論檢定報告，涵蓋時序趨勢、海象交互效應、異常偵測、資源集中度等面向。
      互動式篩選請點右側按鈕進入 Gradio 介面。
    </p>
    <div class="hero-bar">
      <div class="stat">
        <div class="stat-num"><?= $any ? $total_charts : 0 ?></div>
        <div class="stat-lbl">已生成圖表</div>
      </div>
      <div class="stat">
        <div class="stat-num"><?= $stats && !empty($stats['tests']) ? count($stats['tests']) : 0 ?></div>
        <div class="stat-lbl">統計檢定</div>
      </div>
      <div class="stat">
        <div class="stat-num"><?= $latest_ts ? date('m/d', $latest_ts) : '—' ?></div>
        <div class="stat-lbl">最後更新<?= $latest_ts ? '（'.date('H:i', $latest_ts).'）' : '' ?></div>
      </div>
      <div class="stat">
        <div class="stat-num"><?= $has_filter ? '已套用' : '全部資料' ?></div>
        <div class="stat-lbl">資料範圍</div>
      </div>
      <div class="hero-cta">
        <a class="btn primary" href="<?= h($gradio_url) ?>" target="_blank" rel="noopener">
          開啟互動分析介面 →
        </a>
      </div>
    </div>
  </header>

  <?php if (!$any): ?>
    <div class="empty-state">
      <h3>尚未產生分析圖表</h3>
      <p class="muted">請至互動分析介面點擊「執行分析」，或於命令列執行：</p>
      <code>docker compose run --rm analysis python analysis.py</code>
    </div>
  <?php else: ?>

    <!-- 統計洞察區（上方優先呈現） -->
    <?php if ($stats && (!empty($stats['tests']) || !empty($stats['insights']))): ?>
      <section class="dash-section insight-section">
        <div class="section-head">
          <div class="eyebrow">統計洞察</div>
          <h2 class="section-title">推論檢定與資料診斷</h2>
          <p class="section-desc">以假設檢定與描述性統計驗證資料背後的規律，超越「眼觀」階段，提供可被引用的結論。</p>
        </div>

        <?php if (!empty($stats['summary'])): $s = $stats['summary']; ?>
          <div class="kpi-grid">
            <div class="kpi"><div class="kpi-num"><?= h($s['records'] ?? '—') ?></div><div class="kpi-lbl">完成值勤筆數</div></div>
            <div class="kpi"><div class="kpi-num"><?= h($s['people'] ?? '—') ?></div><div class="kpi-lbl">參與人員</div></div>
            <div class="kpi"><div class="kpi-num"><?= h($s['vessels'] ?? '—') ?></div><div class="kpi-lbl">船艦數</div></div>
            <div class="kpi"><div class="kpi-num"><?= h($s['hours_mean'] ?? '—') ?>h</div><div class="kpi-lbl">平均工時</div></div>
            <div class="kpi"><div class="kpi-num"><?= h($s['hours_std'] ?? '—') ?></div><div class="kpi-lbl">工時標準差</div></div>
          </div>
        <?php endif; ?>

        <?php if (!empty($stats['tests'])): ?>
          <div class="test-list">
            <?php foreach ($stats['tests'] as $t):
              $sig = !empty($t['significant']);
            ?>
              <div class="test-item">
                <div class="test-head">
                  <h3 class="test-name"><?= h($t['name']) ?></h3>
                  <?php if ($sig): ?>
                    <span class="badge ok">統計顯著 (p &lt; 0.05)</span>
                  <?php else: ?>
                    <span class="badge off">未達顯著</span>
                  <?php endif; ?>
                </div>
                <div class="test-body">
                  <div class="test-row"><span class="test-lbl">虛無假設 H₀</span><span class="test-val"><?= h($t['h0']) ?></span></div>
                  <div class="test-row"><span class="test-lbl">統計量</span><span class="test-val mono"><?= h($t['statistic']) ?></span></div>
                  <div class="test-row"><span class="test-lbl">p 值</span><span class="test-val mono"><?= h($t['p_display']) ?></span></div>
                  <div class="test-conclusion <?= $sig ? 'sig' : '' ?>"><?= h($t['conclusion']) ?></div>
                </div>
              </div>
            <?php endforeach; ?>
          </div>
        <?php endif; ?>

        <?php if (!empty($stats['insights'])): ?>
          <div class="insight-grid">
            <?php foreach ($stats['insights'] as $ins): ?>
              <div class="insight-card">
                <h3 class="insight-title"><?= h($ins['title']) ?></h3>
                <p class="insight-text"><?= h($ins['text']) ?></p>
              </div>
            <?php endforeach; ?>
          </div>
        <?php endif; ?>

        <?php if (!empty($stats['generated_at'])): ?>
          <div class="muted" style="font-size:12.5px;margin-top:14px;">統計報告生成時間：<?= h($stats['generated_at']) ?></div>
        <?php endif; ?>
      </section>
    <?php endif; ?>

    <!-- 圖表分區 -->
    <?php foreach ($sections as $sec):
      $existing = [];
      foreach ($sec['charts'] as $file => $meta) {
          if (isset($resolved[$file])) $existing[$file] = $meta;
      }
      if (!$existing) continue;
    ?>
      <section class="dash-section">
        <div class="section-head">
          <div class="eyebrow"><?= h($sec['eyebrow']) ?></div>
          <h2 class="section-title"><?= h($sec['title']) ?></h2>
          <p class="section-desc"><?= h($sec['desc']) ?></p>
        </div>

        <div class="chart-grid">
          <?php foreach ($existing as $file => $meta):
            $info = $resolved[$file];
            $disp = basename($info['path']);
            $mtime = date('Y-m-d H:i', $info['mtime']);
          ?>
            <article class="chart-card">
              <div class="chart-head">
                <h3><?= h($meta[0]) ?></h3>
                <span class="muted chart-time"><?= h($mtime) ?></span>
              </div>
              <p class="chart-desc"><?= h($meta[1]) ?></p>
              <img src="analysis_output/<?= h($disp) ?>"
                   alt="<?= h($meta[0]) ?>"
                   loading="lazy">
            </article>
          <?php endforeach; ?>
        </div>
      </section>
    <?php endforeach; ?>

  <?php endif; ?>
</div>
<?php page_footer(); ?>
</body>
</html>
