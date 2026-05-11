<?php
require_once 'auth.php';
require_once 'admin_only.php';
require_once 'ui.php';

$charts = [
    'monthly_trend.png'    => '月度值勤人次趨勢',
    'zone_bar.png'         => '值勤海域分布',
    'zone_sea_stacked.png' => '各海域海況分布',
    'vessel_count.png'     => '各船艦值勤次數',
    'hours_boxplot.png'    => '各海況值勤時數分布',
    'person_heatmap.png'   => '人員月度出勤熱力圖',
    'leave_trend.png'         => '每月核准請假件數',
    'sea_obs_comparison.png'  => '海況分布對照：觀測 vs 模擬（需先執行 fetch_sea_data.py）',
];

$chart_dir  = __DIR__ . '/analysis_output/';
$gradio_url = 'http://localhost:7860';

?>
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>分析儀表板</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<?php nav_top('分析儀表板'); ?>
<div class="wrap" style="padding:2rem 0">

  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem">
    <h2 style="margin:0">資料分析儀表板</h2>
    <a class="btn" href="<?= h($gradio_url) ?>" target="_blank" rel="noopener">
      開啟互動分析介面（Gradio）
    </a>
  </div>

  <?php
  // 檢查是否有任何圖表已產生
  $any = false;
  foreach ($charts as $file => $_) {
      if (file_exists($chart_dir . $file)) { $any = true; break; }
  }
  if (!$any): ?>
    <div class="card" style="text-align:center;padding:3rem;color:#666">
      <p style="font-size:1.1rem">尚未產生分析圖表。</p>
      <p>請至互動分析介面（Gradio）點擊「執行分析」，或執行：</p>
      <code style="background:#f0f0f0;padding:.4rem .8rem;border-radius:4px">
        docker compose run analysis python analysis.py
      </code>
    </div>
  <?php else: ?>

  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:1.5rem">
    <?php foreach ($charts as $file => $title):
      $path = $chart_dir . $file;
      // 若無前綴檔不存在，嘗試 filtered_ 前綴
      if (!file_exists($path)) $path = $chart_dir . 'filtered_' . $file;
      if (!file_exists($path)) continue;
      $file = basename($path);
      $mtime = date('Y-m-d H:i', filemtime($path));
    ?>
    <div class="card" style="padding:1rem">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:.6rem">
        <strong><?= h($title) ?></strong>
        <span class="muted" style="font-size:.8rem">更新：<?= h($mtime) ?></span>
      </div>
      <img src="analysis_output/<?= h($file) ?>"
           alt="<?= h($title) ?>"
           style="width:100%;border-radius:6px;border:1px solid #e0e0e0"
           loading="lazy">
    </div>
    <?php endforeach; ?>
  </div>

  <?php endif; ?>
</div>
</body>
</html>
