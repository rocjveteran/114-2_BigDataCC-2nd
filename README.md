# 海事勤務值勤雲端管理系統

> 114-2 巨量資料與雲端運算 ── 期末專題 ── 第 2 組

延續上學期 PHP + MySQL 值勤管理雛形，改造為 Linux 雲端容器化系統，並整合 Python 資料分析模組與 Gradio 互動儀表板。一指令 `docker compose up` 完成三容器部署。

---

## 組員

| 角色 | 姓名 / 學號 |
|------|------------|
| 組長 | 黃宇平 / C112181108 |
| 組員 | 傅瀚鋌 / C112181112 |
| 組員 | 曾紹喆 / C112181182 |
| 組員 | 劉家样 / C111181141 |
| 組員 | 李翊丞 / C111181134 |
| 組員 | 林秉賢 / C112181148 |

---

## 系統架構

```
                          使用者瀏覽器
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
       :8080 (PHP/Apache)                   :7860 (Gradio)
       ┌──────────────┐                  ┌──────────────────┐
       │  web 容器     │                  │  analysis 容器   │
       │ php:8.2      │                  │ python:3.11     │
       │ - 登入/打卡  │                  │ - Pandas 清洗   │
       │ - 請假審核   │                  │ - Seaborn 圖表  │
       │ - 分析儀表板 │                  │ - Gradio 介面   │
       └───────┬──────┘                  └──────┬───────────┘
               │                                │
               └──── analysis_output volume ────┘
                          (PNG 圖表共享)
                                │
                       ┌────────┴─────────┐
                       │   db 容器        │
                       │   mysql:8.0      │
                       │   maritime_duty  │
                       └──────────────────┘
```

三容器以 Docker Compose 編排，共用內部網路；PHP 與 Python 透過 named volume 共享分析圖表，並連向同一 MySQL 實例。

---

## 技術清單

| 必要技術 | 應用位置 |
|---------|---------|
| **Python + Pandas** | `src/analysis/analysis.py` 資料清洗與統計 |
| **Matplotlib / Seaborn** | 七張視覺化圖表 |
| **Docker / Docker Compose** | `docker/` 三容器架構 |
| **Git / GitHub** | 全部開發歷程 |

| 選擇性技術 | 應用位置 |
|-----------|---------|
| **MySQL 8.0** | `src/app/schema.sql` 三張資料表 |
| **Apache + PHP 8.2** | `src/app/` 22 個 PHP 檔 |
| **Gradio** | `src/analysis/app.py` 互動分析介面 |
| **Jupyter Notebook** | `notebooks/eda.ipynb` 探索性資料分析 |

---

## 快速啟動

### 必要環境

- Docker Desktop 4.x 以上（Windows + WSL2 / macOS / Linux 皆可）
- 約 2 GB 可用磁碟空間（映像檔 + 模擬資料）

### 步驟

```bash
# 1. clone 專案
git clone https://github.com/rocjveteran/114-2_BigDataCC-2nd.git
cd 114-2_BigDataCC-2nd

# 2. 建立環境變數檔（.env 需放在 docker/ 目錄內）
cp .env.example docker/.env
# 編輯 docker/.env，填入 DB 密碼（CWA_API_KEY 可留空）

# 3. 啟動三容器（首次會建置映像，約 3–5 分鐘）
cd docker
docker compose up --build

# 4. 首次使用：產生模擬資料 + 圖表（另開終端機）
docker compose run analysis python generate_mock_data.py
docker compose run analysis python analysis.py

# 5.（選用）開啟 Jupyter 進行探索性分析
docker compose run -p 8888:8888 analysis \
  jupyter notebook --ip=0.0.0.0 --no-browser --allow-root /notebooks
```

### 存取服務

容器啟動後在瀏覽器打開：

| 服務 | 網址 | 說明 |
|------|------|------|
| **登入頁** | **http://localhost:8080/login.php** | 系統入口（首頁也會自動轉跳到此） |
| PHP 系統首頁 | http://localhost:8080 | `index.php` 會 redirect 到登入或值勤頁 |
| 分析儀表板 | http://localhost:8080/admin_dashboard.php | 顯示 7 張 Python 圖表（需管理員以上） |
| Gradio 互動分析 | http://localhost:7860 | 篩選日期/海域/船艦，即時產圖 |

> PHP 檔案不能直接用檔案總管雙擊開啟（會跳出原始碼），必須走 Apache 服務（即上方 `localhost:8080` 網址），所以**先確認三個容器都在 Up 狀態**再開瀏覽器。

### 預設帳號

| 帳號 | 角色 | 密碼 |
|------|------|------|
| boss1 | 老闆 | （見 `src/app/schema.sql` 註解） |
| admin1 | 管理員 | （見 `src/app/schema.sql` 註解） |
| em1 | 員工 | （見 `src/app/schema.sql` 註解） |
| chen_wei, lin_jia, ... | 員工 | `maritime2025` |

---

## 操作步驟（端到端流程）

完整跑一次以驗收系統功能：

1. **打開登入頁** → http://localhost:8080/login.php
2. **以 boss1 登入**（管理者權限）
3. **打卡測試**：點上方「值勤」→ 按「開始值勤」→ 再按「結束值勤」
4. **看個人紀錄**：點「我的紀錄」確認剛才打卡有出現
5. **試請假**：點「請假」→ 填日期/假別 → 送出
6. **管理員審核**：點「請假審核」→ 把剛才送出的請假核准
7. **看勤務總覽**：點「勤務總覽」→ 切換日期查看全員狀態
8. **產生分析圖表**：點「分析儀表板」右上「開啟互動分析介面」→ 跳到 Gradio (http://localhost:7860) → 點「執行分析」
9. **回 PHP 儀表板**：重整 http://localhost:8080/admin_dashboard.php → 應看到 7 張圖表
10. **下載日報表**：勤務總覽右上「匯出日報表」會下載當日 CSV

---

## 換到另一台電腦重新開啟（例如帶到學校）

### 第一次部署（新機器，從 0 開始）

```bash
# 1. 確認已裝好 Docker Desktop 並啟動（系統匣有鯨魚圖示且為綠燈）

# 2. clone 專案
git clone https://github.com/rocjveteran/114-2_BigDataCC-2nd.git
cd 114-2_BigDataCC-2nd

# 3. 建立 docker/.env（.gitignore 不會推這個檔，必須手動建）
cp .env.example docker/.env
# 或在 Windows PowerShell：
#   Copy-Item .env.example docker/.env
# 然後用編輯器打開 docker/.env，把 change_me_root 與 change_me_user 改成你想要的密碼

# 4. 啟動三容器（首次會建置映像，大約 3–5 分鐘）
cd docker
docker compose up --build -d

# 5. 等 DB 就緒（約 20–30 秒）後產生模擬資料 + 圖表
docker compose run --rm analysis python generate_mock_data.py
docker compose run --rm analysis python analysis.py

# 6. 開瀏覽器 → http://localhost:8080/login.php
```

### 第二次以後（同一台機器）

關機後再開機只需：

```bash
cd 114-2_BigDataCC-2nd/docker
docker compose up -d
```

容器會記得上次的資料庫內容（`db_data` named volume 持久化）與分析圖表（`analysis_output` named volume），所以**不需要重新跑 generate_mock_data.py 或 analysis.py**，除非你想重新生成。

### 完全停止

```bash
cd docker
docker compose down              # 停容器但保留資料
docker compose down -v           # 連 DB 資料一起清掉（要重灌時用）
```

### 常見狀況

| 症狀 | 處理 |
|------|------|
| `localhost:8080` 連不上 | `docker compose ps` 看 web 是否 Up；若 Exit，跑 `docker compose logs web` 看錯誤 |
| 登入頁顯示 DB 連線失敗 | 檢查 `docker/.env` 是否存在、密碼是否與容器一致；可 `docker compose down -v && docker compose up --build` 重灌 |
| 分析儀表板顯示「尚未產生圖表」 | 跑 `docker compose run --rm analysis python analysis.py`，或從 Gradio 點「執行分析」 |
| Gradio 介面打不開 | `docker compose logs analysis` 看是否 import error，多半是建置時 pip 沒裝完 |
| 中文字變方塊 | 重建 analysis 容器 `docker compose build --no-cache analysis` 強制重灌字型 |

---

## 專案結構

```
114-2_BigDataCC-2nd/
│
├── README.md                  ← 本檔案
├── .env.example               ← 資料庫連線變數範本
├── .gitignore
├── requirements.txt           ← Python 套件需求
│
├── docker/                    ← Docker 容器配置
│   ├── docker-compose.yml     ← 三容器編排
│   ├── web/Dockerfile         ← php:8.2-apache
│   └── analysis/Dockerfile    ← python:3.11-slim + fonts-noto-cjk
│
├── src/
│   ├── app/                   ← PHP 應用程式（22 檔案）
│   │   ├── db.php             ← PDO 連線（讀取環境變數）
│   │   ├── schema.sql         ← MySQL schema（含海事擴充欄位）
│   │   ├── login.php / auth.php / logout.php
│   │   ├── punch.php / records.php / leave.php
│   │   ├── admin_*.php        ← 管理介面
│   │   ├── admin_dashboard.php ← 分析儀表板
│   │   ├── ui.php / style.css
│   │   └── ...
│   │
│   └── analysis/              ← Python 分析程式
│       ├── generate_mock_data.py  ← 模擬資料生成
│       ├── analysis.py            ← 資料清洗 + 7 張圖表
│       └── app.py                 ← Gradio 互動介面
│
├── notebooks/                 ← Jupyter Notebook（探索分析）
├── data/                      ← 原始與清洗後資料
│
├── docs/
│   ├── report.md              ← 期末報告
│   └── slides_outline.md      ← 投影片大綱
│
├── proposal/
│   └── proposal.md            ← 專題提案
│
└── my-topics/                 ← 個人題目構想
```

---

## 主要功能

### PHP 系統 (port 8080)

| 頁面 | 功能 | 角色限制 |
|------|------|---------|
| 登入 / 登出 | Session 認證 | 全部 |
| 上下勤打卡 | 含當日狀態顯示 | 全部 |
| 我的值勤 | 個人歷史記錄 | 全部 |
| 請假申請 | 起訖日、假別、事由 | 全部 |
| 值勤總覽 | 全員當日狀態 | 管理員以上 |
| 請假審核 | 核准 / 拒絕 | 管理員以上 |
| 帳號管理 | 新增、停用、改密 | 管理員以上 |
| **分析儀表板** | 顯示 7 張 Python 圖表 | 管理員以上 |
| CSV 匯出 | 值勤記錄下載 | 管理員以上 |

### Python 分析模組

七張分析圖表，輸出至 `analysis_output/` 共用 volume：

1. `monthly_trend.png` — 月度值勤人次趨勢
2. `zone_bar.png` — 值勤海域分布
3. `zone_sea_stacked.png` — 各海域海況分布
4. `vessel_count.png` — 各船艦值勤次數
5. `hours_boxplot.png` — 各海況值勤時數箱型圖
6. `person_heatmap.png` — 人員月度出勤熱力圖
7. `leave_trend.png` — 每月核准請假件數

### Gradio 互動介面 (port 7860)

- 日期區間篩選
- 海域勾選（港口 / 近海 / 外海，可多選）
- 船艦下拉（從 DB 動態載入，可多選）
- 即時執行分析，2 欄網格顯示 7 張圖

---

## 資料 Schema 設計

`attendance` 表本學期擴充三個海事業務欄位：

```sql
duty_zone  ENUM('港口','近海','外海')   NULL,
sea_state  ENUM('平靜','輕浪','中浪','大浪') NULL,
vessel_id  VARCHAR(20)                   NULL,
```

模擬資料機率模型：

| 海況 \ 海域 | 港口 | 近海 | 外海 |
|-----------|------|------|------|
| 平靜 | 70% | 40% | 15% |
| 輕浪 | 25% | 35% | 30% |
| 中浪 | 4% | 20% | 35% |
| 大浪 | 1% | 5% | **20%** |

外海大浪天會提前下勤 100 分鐘，模擬實際海象對勤務時數的影響。

---

## 開發指引

### Commit 訊息格式

```
[分類] 說明

[data]      資料相關（生成、來源說明）
[analysis]  分析程式（Pandas、視覺化）
[docker]    容器化（Dockerfile、compose）
[app]       PHP 應用程式
[docs]      文件
[fix]       修正錯誤
[chore]     雜項清理
```

### 安全規範

- ✅ `db.php` 不寫死 DB 帳號密碼，改讀環境變數
- ✅ `.env` 已加入 `.gitignore`，不推送至 GitHub
- ✅ PHP 使用 PDO prepared statement 防 SQL Injection
- ✅ MySQL 使用非 root 帳號連線應用程式

---

## 文件索引

| 文件 | 用途 |
|------|------|
| [proposal/proposal.md](proposal/proposal.md) | 專題提案 |
| [docs/report.md](docs/report.md) | 期末報告（十章） |
| [docs/slides_outline.md](docs/slides_outline.md) | 投影片大綱 |
| [docs/demo_script.md](docs/demo_script.md) | Demo 演練腳本 |

---

## 授權

本專案為學校課程作業，僅供學術參考。模擬資料為自有生成，不含真實人員資訊。
