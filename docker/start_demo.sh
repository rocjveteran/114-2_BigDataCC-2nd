#!/usr/bin/env bash
# start_demo.sh — 一鍵啟動三容器 + 植入模擬資料 + 產生分析圖表
# 用法：在 repo 根目錄執行  bash docker/start_demo.sh
# 或進入 docker/ 目錄後執行  bash start_demo.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"   # 確保 .env 與 docker-compose.yml 在同一目錄

echo "=== [1/4] 啟動三容器（背景） ==="
docker compose up -d --build

echo "=== [2/4] 等待 MySQL 健康檢查通過（最多 60 秒）==="
for i in $(seq 1 12); do
  STATUS=$(docker compose ps db --format '{{.Health}}' 2>/dev/null || echo "waiting")
  if [ "$STATUS" = "healthy" ]; then
    echo "  DB 已就緒（第 ${i} 次檢查）"
    break
  fi
  echo "  等待中... ($((i*5))s)"
  sleep 5
done

echo "=== [3/4] 植入六個月模擬值勤資料 ==="
DBROOT=$(grep -m1 '^DB_ROOT_PASS=' .env 2>/dev/null | cut -d= -f2-)
EXISTING=0
if [ -n "$DBROOT" ]; then
  EXISTING=$(docker compose exec -T db mysql -uroot -p"$DBROOT" maritime_duty -sN \
    -e "SELECT COUNT(*) FROM attendance;" 2>/dev/null | grep -E '^[0-9]+$' | head -1 || echo "0")
fi
EXISTING=${EXISTING:-0}
if [ "$EXISTING" -gt 100 ] && [ "${1}" != "--fresh" ]; then
  echo "  已有 $EXISTING 筆資料，略過（加 --fresh 參數可強制重植）"
else
  docker compose run --rm analysis python generate_mock_data.py
fi

echo "=== [4/5] 植入海象觀測資料（CWA 浮標，無金鑰自動季節性模擬備援）==="
docker compose run --rm analysis python fetch_sea_data.py

echo "=== [5/5] 產生 21 張統計圖表 + 排班引擎 + Folium 地圖 + ML 模型 ==="
docker compose run --rm analysis python analysis.py

# 確保種子帳號密碼為 demo1234（schema.sql 已內建，此步為保險）
docker compose run --rm web php /var/www/html/reset_demo_pw.php >/dev/null 2>&1 || true

echo ""
echo "=================================="
echo "  完成！開啟以下網址："
echo "  PHP 系統：    http://localhost:8080/login.php"
echo "  明日排班：    http://localhost:8080/scheduler.php"
echo "  分析儀表板：  http://localhost:8080/admin_dashboard.php"
echo "  Gradio：      http://localhost:7860"
echo "  預設帳號（密碼 demo1234）："
echo "    boss1  / demo1234（老闆）"
echo "    admin1 / demo1234（管理員）"
echo "    em1    / demo1234（員工）"
echo "    其餘模擬人員 / maritime2025"
echo "=================================="
