<?php
/**
 * reset_demo_pw.php — 將三個種子帳號密碼重設為 demo1234（僅供本機 / Demo 用）。
 *
 * 用法（CLI / 容器內）：
 *   docker compose run --rm web php /var/www/html/reset_demo_pw.php
 *
 * 安全防護：本腳本僅允許從命令列（CLI）執行，透過 HTTP 存取會直接拒絕，
 * 避免被瀏覽器觸發而成為密碼重設後門。正式部署請直接刪除本檔。
 */

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit("Forbidden: this script is CLI-only.\n");
}

require __DIR__ . '/db.php';

$demo_pw = getenv('DEMO_PW') ?: 'demo1234';
$accounts = ['boss1', 'admin1', 'em1'];

$hash = password_hash($demo_pw, PASSWORD_BCRYPT);
$stmt = $pdo->prepare("UPDATE users SET password_hash = ? WHERE username = ?");

$done = 0;
foreach ($accounts as $u) {
    $stmt->execute([$hash, $u]);
    $done += $stmt->rowCount();
    echo "  ✔ {$u} 密碼已重設\n";
}

echo "完成：{$done} 個帳號密碼已設為 \"{$demo_pw}\"。\n";
