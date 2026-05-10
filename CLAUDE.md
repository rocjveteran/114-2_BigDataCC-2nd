# 海事勤務值勤雲端管理系統 — 專題開發指南

本檔案為 Claude Code 啟動時讀取之脈絡交接文件，記錄本專題之背景、技術決策、開發規範與當前進度。請於每次新對話啟動前先閱讀本檔案。

## 專題背景

本專題為「114-2 巨量資料與雲端運算」期末作業，第 2 組（組長：黃宇平）。系統前身為上學期 114-1 完成之 PHP + MySQL 值勤管理雛形，原運行於 XAMPP / Windows 環境。本學期目標為將其改造為符合課程必要技術之 Linux 雲端容器化系統，並補上資料分析與視覺化能力。

評分標準總分 100 分：專題提案 10、資料分析品質 20、程式碼品質 20、Docker 部署 20、GitHub 管理 10、口頭報告與 Demo 15、文件完整度 5。

## 執行模式

組別形式維持五人，實際技術實作由組長一人執行，已徵得授課教師同意。組員負責文件校對、測試、簡報配合等支援性工作。Commit 紀錄將以組長帳號 `rocjveteran` 為主。

開發策略採 vibe coding：以 Claude Code 主導程式生成，目標為「能成功執行」而非「徹底理解」，在期限內交付完整可運行系統。所有重大架構變更前先讓組長 review diff。

## 技術架構（已定案）

採三容器架構，由 Docker Compose 編排：

- **web**：`php:8.2-apache`，承載上學期 PHP 系統並完成 Linux 化改造
- **db**：`mysql:8.0`，存放使用者、值勤、請假與海象資料
- **analysis**：`python:3.11`，執行 Pandas 分析、Matplotlib/Seaborn 圖表生成、Gradio 互動介面

三容器共用 Docker 內部網路。PHP 與 Python 皆連向同一 MySQL 服務（host name 為 `db`）。分析結果以 PNG 與 HTML 形式輸出至共用 named volume，由 PHP 端嵌入顯示。

## 必要與選擇性技術勾選

| 項目 | 狀態 | 類型 |
|------|------|------|
| Python + Pandas 資料分析 | ✅ | 必要 |
| Matplotlib / Seaborn 視覺化 | ✅ | 必要 |
| Docker 容器化 | ✅ | 必要 |
| Git / GitHub 管理 | ✅ | 必要 |
| MySQL 資料庫 | ✅ | 選擇性 |
| Apache + PHP 前端 | ✅ | 選擇性 |
| Jupyter Notebook | ✅ | 選擇性 |
| Gradio 互動介面 | ✅ | 選擇性 |
| Keras 預訓練模型 | ❌ | 選擇性（暫不納入以控制範圍） |

## Schema 擴充計畫

於上學期 `attendance` 表新增三個欄位以強化海事業務特性：

```sql
ALTER TABLE attendance
  ADD COLUMN duty_zone ENUM('港口','近海','外海') NULL,
  ADD COLUMN sea_state ENUM('平靜','輕浪','中浪','大浪') NULL,
  ADD COLUMN vessel_id VARCHAR(20) NULL;
```

以 Python 腳本生成 6 個月模擬值勤資料（約 800–1200 筆），可選擇接入中央氣象署海洋觀測公開資料補強海象欄位真實性。模擬資料生成邏輯需考量人員輪班規則、海域與海象之合理機率分布。

## 安全規範

- `db.php` 不得寫死 root 帳號與空密碼，改以環境變數讀取（`getenv('DB_HOST')` 等）
- 上學期之 `init_admin.php`（如有）部署後立即刪除
- 任何敏感檔（含預設密碼、API key）不得 commit 至 GitHub
- `.gitignore` 須包含 `.env`、`*.log`、`__pycache__/`、`.ipynb_checkpoints/`

## Repo 待清理項目

當前 repo 由模板生成，含以下異常須修正：

1. 根目錄 `Hollow UP` 為誤推檔案，應刪除
2. `my-topics/my-topics/` 為錯誤巢狀資料夾結構，應扁平化或刪除
3. `README.md` 為模板原文，須改寫為本組實際內容
4. `src/`、`docker/`、`notebooks/` 等資料夾僅含 `.gitkeep`，待填入實質內容

## 上學期 PHP 程式碼

上學期專案共 22 個檔案，包含 `db.php`、`auth.php`、`punch.php`、`leave.php`、`admin_*.php` 系列、`schema.sql`、`style.css`、`ui.php`。組長將提供原始檔案，請置入 `src/app/` 之下並完成 Linux 化改造。

## 開發優先順序

| 週次 | 起訖日期 | 預計完成項目 |
|------|---------|------------|
| 第 14 週 | 5 / 12 – 5 / 18 | Docker 環境建置、PHP 系統 Linux 化、Schema 擴充、模擬資料生成 |
| 第 15 週 | 5 / 19 – 5 / 25 | Python 資料清洗、Pandas 統計分析、Matplotlib/Seaborn 圖表 |
| 第 16 週 | 5 / 26 – 6 / 1 | Gradio 互動介面、PHP 端分析儀表板整合、整合測試 |
| 第 17 週 | 6 / 2 – 6 / 8 | 期末報告 `docs/report.md`、投影片、Demo 演練 |
| 第 18 週 | 6 / 9 – 6 / 15 | 期末口頭報告與 Demo |

## Commit 訊息格式

依專題 README 規範：

- `[data]` 資料相關（如生成模擬資料、新增資料來源說明）
- `[analysis]` 分析程式（Pandas 處理、視覺化）
- `[docker]` 容器化（Dockerfile、docker-compose.yml）
- `[app]` PHP 應用程式修改
- `[docs]` 文件（README、報告、投影片）
- `[fix]` 修正錯誤
- `[chore]` 雜項清理（如刪除 Hollow UP）

範例：`[docker] 建立三容器 docker-compose 配置`

## 開發環境

- 組長作業系統：Windows
- 預期容器執行環境：Linux（透過 Docker Desktop with WSL2 後端）
- IDE：VS Code 搭配 Claude Code extension
- 模型選擇：日常 vibe coding 用 Sonnet；架構決策、Docker 啟動失敗除錯、多檔案連動修不好時切換 Opus

## 第一個任務（建議起手指令）

啟動 Claude Code 後第一個指令建議為：

> 請先掃描整個 repo 並讀取 CLAUDE.md 確認脈絡，接著依第 14 週目標處理以下事項。每一項完成前先讓我 review diff，確認後再 commit。
> 
> 1. 整理 `my-topics/` 結構，扁平化或移除巢狀的 `my-topics/my-topics/` 資料夾
> 2. 將我提供的上學期 PHP 程式碼置入 `src/app/` 之下
> 3. 建立 `docker/docker-compose.yml` 與相關 `Dockerfile`，依 CLAUDE.md 之三容器架構
> 4. 修改 `db.php` 改為從環境變數讀取連線設定
> 5. 撰寫 Schema migration SQL，新增 `duty_zone`、`sea_state`、`vessel_id` 三個欄位

完成後再進入 Python 模擬資料生成腳本之開發。
