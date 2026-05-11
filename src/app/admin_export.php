<?php
require 'admin_only.php';
require 'db.php';
require_once 'ui.php';

date_default_timezone_set('Asia/Taipei');

$d = $_GET['d'] ?? date('Y-m-d');

// Fetch users + attendance of that date
$users = $pdo->query("SELECT user_id, username, full_name FROM users ORDER BY user_id ASC")->fetchAll();

$stmt = $pdo->prepare("SELECT user_id, work_date, check_in, check_out, status FROM attendance WHERE work_date=?");
$stmt->execute([$d]);
$map = [];
foreach ($stmt->fetchAll() as $a) {
  $map[(int)$a['user_id']] = $a;
}

// approved leave map
$stmt = $pdo->prepare("SELECT user_id, leave_type FROM leaves WHERE status='approved' AND date_from<=? AND date_to>=?");
$stmt->execute([$d, $d]);
$lmap = [];
foreach ($stmt->fetchAll() as $x) { $lmap[(int)$x['user_id']] = $x['leave_type']; }

header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="duty_'.$d.'.csv"');

$out = fopen('php://output', 'w');
// UTF-8 BOM for Excel
fprintf($out, chr(0xEF).chr(0xBB).chr(0xBF));

fputcsv($out, ['user_id','username','full_name','work_date','check_in','check_out','status','leave']);

foreach ($users as $u) {
  $uid = (int)$u['user_id'];
  $a = $map[$uid] ?? null;

  $work_date = $d;
  $check_in  = $a['check_in'] ?? '';
  $check_out = $a['check_out'] ?? '';
  $status    = $a ? ($a['status'] ?? '') : 'none';
  $leave     = $lmap[$uid] ?? '';

  fputcsv($out, [$uid, $u['username'], $u['full_name'], $work_date, $check_in, $check_out, $status, $leave]);
}
fclose($out);
exit;