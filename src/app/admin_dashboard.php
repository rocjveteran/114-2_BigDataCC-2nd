<?php
require_once 'auth.php';
require_once 'admin_only.php';
require_once 'ui.php';

$chart_dir  = __DIR__ . '/analysis_output/';
$gradio_url = 'http://localhost:7860';

// 章節分組：每組 = [eyebrow, 標題, 描述, [檔名 => [圖表名, 一行說明]]]
$sections = [
    [
        'eyebrow' => '時序趨勢',
        'title'   => '值勤與請假月度走勢',
        'desc'    => '從時間軸觀察整體工作量與請假申請的波動，找出尖峰月份與淡季區間。',
        'charts'  => [
            'monthly_trend.png' => ['月度值勤人次趨勢', '每月累計的值勤人次變化。'],
            'leave_trend.png'   => ['每月核准請假件數', '核准請假數的月度趨勢，反映人力可用度。'],
        ],
    ],
    [
        'eyebrow' => '任務分布',
        'title'   => '海域、海況與工時',
        'desc'    => '比較不同海域、海況條件下的值勤分布與單次時數差異。',
        'charts'  => [
            'zone_bar.png'           => ['值勤海域分布', '港口、近海、外海三類海域的值勤次數。'],
            'zone_sea_stacked.png'   => ['各海域海況分布', '每個海域在不同海況下的比例堆疊圖。'],
            'hours_boxplot.png'      => ['各海況值勤時數分布', '海況等級對單次值勤時數的影響（盒鬚圖）。'],
            'sea_obs_comparison.png' => ['海況對照：觀測 vs 模擬', '模擬資料與中央氣象署觀測值的海況分布比對（需先執行 fetch_sea_data.py）。'],
        ],
    ],
    [
        'eyebrow' => '資源使用',
        'title'   => '船艦調度與人員出勤',
        'desc'    => '觀察各船艦使用頻率與人員月度出勤密度，輔助派遣與輪值決策。',
        'charts'  => [
            'vessel_count.png'  => ['各船艦值勤次數', '各艘船艦被派遣的累計次數排行。'],
            'person_heatmap.png'=> ['人員月度出勤熱力圖', '每位員工每月的出勤密度，紅色越深代表越頻繁。'],
        ],
    ],
];

// 解析所有圖表的實際路徑（含 filtered_ 前綴 fallback）
$resolved   = []; // file => ['path' => ..., 'mtime' => ...]
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
?>
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>分析儀表板 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
<?php nav_top(); ?>
<div class="wrap" style="padding:2.5rem 16px 3rem">

  <!-- Hero -->
  <header class="hero">
    <div class="eyebrow">資料分析 · Analysis</div>
    <h1 class="hero-title">海事勤務分析儀表板</h1>
    <p class="lead">
      以六個月實際與模擬值勤資料生成統計圖表，協助觀察人員調度、海域分布、海況影響、請假趨勢等面向。
      <br>互動式篩選請點右側按鈕進入 Gradio 介面。
    </p>
    <div class="hero-bar">
      <div class="stat">
        <div class="stat-num"><?= $any ? $total_charts : 0 ?></div>
        <div class="stat-lbl">已生成圖表</div>
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
      <div class="empty-icon"><?= icon_svg('list') ?></div>
      <h3>尚未產生分析圖表</h3>
      <p class="muted">請至互動分析介面點擊「執行分析」，或於命令列執行：</p>
      <code>docker compose run analysis python analysis.py</code>
    </div>
  <?php else: ?>

    <?php foreach ($sections as $sec):
      // 過濾出本節實際存在的圖
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
