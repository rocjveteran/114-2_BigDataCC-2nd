#!/bin/bash
# ---------------------------------------------------------------------------
# setup_web.sh — 無 Docker 的本機 / 沙箱一鍵環境準備
# ---------------------------------------------------------------------------
# 適用情境：Docker image pull 受限的環境（例如 Claude Code on the web 沙箱），
# 以「原生 MariaDB + 既有 PHP / Python」重建等價於 docker-compose 的執行環境，
# 供分析驗證、PHP 頁面與 Gradio 介面實跑 / 截圖之用。
#
# 動作（皆冪等，可重複執行）：
#   1. 確認 Python 相依與中文字型（缺少時自動補裝）
#   2. 啟動 MariaDB（若未執行）
#   3. 建立資料庫與應用帳號、必要時載入 schema
#   4. 將三個種子帳號（boss1 / admin1 / em1）密碼設為 demo1234（僅本機示範用）
#   5. 清空並重灌「相對今天」的模擬值勤資料
#   6. 渲染 15 張分析圖至 src/app/analysis_output/
#   7. 印出啟動 PHP / Gradio 的指令與登入資訊
#
# 注意：本腳本僅供「無 Docker」的開發 / 驗證環境；正式部署請改用 docker/。
#       過程會使用 sudo 啟動 MariaDB 並管理資料庫。
#
# 用法：  bash scripts/setup_web.sh
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DB_NAME="${DB_NAME:-maritime_duty}"
DB_USER="${DB_USER:-maritime_user}"
DB_PASS="${DB_PASS:-devpass_local_only}"
DEMO_PW="${DEMO_PW:-demo1234}"
SOCK=/run/mysqld/mysqld.sock

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# 1. Python 相依 + 中文字型 -----------------------------------------------
say "檢查 Python 相依與中文字型"
if ! python3 -c "import pandas, numpy, matplotlib, seaborn, scipy, mysql.connector, bcrypt" >/dev/null 2>&1; then
  echo "缺少分析相依，安裝 requirements.txt …"
  python3 -m pip install --quiet -r requirements.txt
else
  echo "Python 分析相依：已就緒"
fi
if ! fc-list 2>/dev/null | grep -qi "noto.*cjk"; then
  echo "安裝中文字型 fonts-noto-cjk …"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq fonts-noto-cjk >/dev/null 2>&1 || true
else
  echo "CJK 中文字型：已就緒"
fi

# 2. MariaDB ---------------------------------------------------------------
say "確保 MariaDB 執行中"
if ! pgrep -x mariadbd >/dev/null 2>&1; then
  sudo mkdir -p /run/mysqld && sudo chown mysql:mysql /run/mysqld
  if [ ! -d /var/lib/mysql/mysql ]; then
    sudo mariadb-install-db --user=mysql --datadir=/var/lib/mysql >/dev/null 2>&1
  fi
  sudo -u mysql /usr/sbin/mariadbd --datadir=/var/lib/mysql \
       --socket="$SOCK" --bind-address=127.0.0.1 --port=3306 >/tmp/mariadbd.log 2>&1 &
  for _ in $(seq 1 30); do
    sudo mysqladmin --socket="$SOCK" ping >/dev/null 2>&1 && break
    sleep 1
  done
fi
sudo mysqladmin --socket="$SOCK" ping >/dev/null 2>&1 \
  && echo "MariaDB：執行中" || { echo "MariaDB 啟動失敗，請查看 /tmp/mariadbd.log"; exit 1; }

# 3. 資料庫 + 帳號 + schema ------------------------------------------------
say "建立資料庫與應用帳號"
sudo mysql --socket="$SOCK" <<SQL
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$DB_PASS';
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'127.0.0.1';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL

if ! sudo mysql --socket="$SOCK" "$DB_NAME" -e "SELECT 1 FROM users LIMIT 1" >/dev/null 2>&1; then
  say "載入 schema.sql"
  sudo mysql --socket="$SOCK" "$DB_NAME" < src/app/schema.sql
else
  echo "schema 已存在，略過載入"
fi

# 4. 種子帳號示範密碼 ------------------------------------------------------
say "設定種子帳號（boss1 / admin1 / em1）密碼為 $DEMO_PW（僅本機示範）"
HASH="$(php -r "echo password_hash('$DEMO_PW', PASSWORD_BCRYPT);")"
sudo mysql --socket="$SOCK" "$DB_NAME" \
  -e "UPDATE users SET password_hash='$HASH' WHERE username IN ('boss1','admin1','em1');"

# 5. 重灌模擬資料 ----------------------------------------------------------
say "清空並重灌模擬值勤資料（相對今天）"
sudo mysql --socket="$SOCK" "$DB_NAME" \
  -e "SET FOREIGN_KEY_CHECKS=0; TRUNCATE attendance; TRUNCATE leaves; SET FOREIGN_KEY_CHECKS=1;"
( cd src/analysis && \
  DB_HOST=127.0.0.1 DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASS="$DB_PASS" \
  python3 generate_mock_data.py )

# 6. 渲染圖表 --------------------------------------------------------------
say "渲染分析圖至 src/app/analysis_output/"
mkdir -p src/app/analysis_output
rm -f src/app/analysis_output/*.png src/app/analysis_output/*.json
( cd src/analysis && \
  DB_HOST=127.0.0.1 DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASS="$DB_PASS" \
  OUTPUT_DIR="$ROOT/src/app/analysis_output" python3 analysis.py >/dev/null )
echo "已輸出： $(ls src/app/analysis_output/*.png 2>/dev/null | wc -l) 張圖"

# 7. 啟動指引 --------------------------------------------------------------
cat <<INFO

================================================================
 環境就緒。手動啟動服務：

 PHP 系統 (http://127.0.0.1:8080)：
   DB_HOST=127.0.0.1 DB_NAME=$DB_NAME DB_USER=$DB_USER DB_PASS=$DB_PASS APP_ENV=dev \\
     php -S 127.0.0.1:8080 -t src/app

 Gradio 介面 (http://127.0.0.1:7860)：
   cd src/analysis && DB_HOST=127.0.0.1 DB_NAME=$DB_NAME DB_USER=$DB_USER DB_PASS=$DB_PASS \\
     OUTPUT_DIR=$ROOT/src/app/analysis_output python3 app.py

 登入帳號： boss1 / admin1 / em1     密碼： $DEMO_PW
================================================================
INFO
