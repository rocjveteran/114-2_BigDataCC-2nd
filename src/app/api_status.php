<?php
/**
 * api_status.php — 即時艦上狀態 JSON endpoint（供儀表板每 60 秒輪詢自動刷新）。
 * 需登入；回傳今日在勤/已下勤/請假/未值勤人數、即時海況與時間戳。
 */
require 'auth.php';
require 'db.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

date_default_timezone_set('Asia/Taipei');
$today = date('Y-m-d');

// 今日艦上配置
$stmt = $pdo->prepare("
  SELECT u.user_id,
         a.check_in, a.check_out,
         (SELECT leave_type FROM leaves lv WHERE lv.user_id=u.user_id AND lv.status='approved'
            AND lv.date_from<=? AND lv.date_to>=? LIMIT 1) AS lv_type
  FROM users u
  LEFT JOIN attendance a ON a.user_id=u.user_id AND a.work_date=?
  WHERE u.is_active=1");
$stmt->execute([$today, $today, $today]);
$rows = $stmt->fetchAll();

$on = $done = $leave = $off = 0;
foreach ($rows as $r) {
  if ($r['lv_type'])                                         $leave++;
  elseif (!empty($r['check_in']) && empty($r['check_out']))  $on++;
  elseif (!empty($r['check_out']))                           $done++;
  else                                                       $off++;
}
$total = count($rows);

// 即時海況（讀 recommendations.json 的 sea_now）
$sea_now = null;
$output_dir = getenv('OUTPUT_DIR') ?: '/app/output';
$rec_path   = $output_dir . '/recommendations.json';
if (!file_exists($rec_path) && file_exists(__DIR__ . '/analysis_output/recommendations.json')) {
  $rec_path = __DIR__ . '/analysis_output/recommendations.json';
}
if (file_exists($rec_path)) {
  $rec = @json_decode(file_get_contents($rec_path), true);
  if ($rec) $sea_now = $rec['sea_now'] ?? null;
}

echo json_encode([
  'ts'       => date('H:i:s'),
  'date'     => $today,
  'crew'     => ['on' => $on, 'done' => $done, 'leave' => $leave, 'off' => $off, 'total' => $total],
  'on_duty'  => $on + $done,
  'sea_now'  => $sea_now,
], JSON_UNESCAPED_UNICODE);
