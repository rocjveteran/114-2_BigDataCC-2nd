# 期末專題報告

## 組別資訊

| 項目 | 內容 |
|------|------|
| 課程 | 114-2 巨量資料與雲端運算 |
| 組別 | 第 2 組 |
| 專題名稱 | 海事勤務值勤雲端管理系統 |
| 組長 | 黃宇平 / C112181108 |
| 組員 | 傅瀚鋌 / C112181112 |
| 組員 | 曾紹喆 / C112181182 |
| 組員 | 劉家样 / C111181141 |
| 組員 | 李翊丞 / C111181134 |
| 組員 | 林秉賢 / C112181148 |
| 報告日期 | 2026 年 6 月 |

---

## 摘要

本專題延續上學期完成之 PHP + MySQL 海事勤務值勤管理雛形，將其改造為符合課程要求之 Linux 雲端容器化系統。系統採三容器 Docker Compose 架構，涵蓋 PHP/Apache 前端、MySQL 資料庫與 Python 分析服務，可以單一指令完成部署。

在資料端，以 Python 腳本生成六個月、逾千筆含海域、海況、船艦編號等欄位的模擬值勤資料，並以 Pandas 進行清洗與統計分析，產出七張 Matplotlib/Seaborn 視覺化圖表。互動端透過 Gradio 提供可即時篩選的分析儀表板，PHP 端亦設有整合顯示頁面。

本系統完整覆蓋課程必要技術（Python + Pandas、Matplotlib/Seaborn、Docker、Git/GitHub）及多項選擇性技術（MySQL、Apache + PHP、Jupyter、Gradio），具備海事領域特性，可作為實際部署之管理工具基礎。

---

## 一、專題動機與目標

### 1.1 背景

本組於 114-1 學期完成「海事勤務值勤管理系統」雛形，採 PHP + MySQL 架構，運行於 Windows XAMPP 環境，具備登入認證、值勤打卡（上下勤）、請假申請與審核、三層級權限管理（老闆／管理員／員工）等功能，共 22 個 PHP 檔案。

然而原系統存在三項主要不足：

1. **部署侷限**：強依賴 Windows + XAMPP，無法跨平台移轉，亦不符雲端運維需求
2. **缺乏分析能力**：系統僅累積值勤記錄，管理層無法從歷史資料掌握人力分布、工時負荷、海象與值勤量之關聯等趨勢
3. **業務特性不足**：現有 schema 為通用打卡系統，未反映海事勤務特有之海域、海況、船艦等業務維度

### 1.2 目標

| 目標 | 對應技術 |
|------|---------|
| 跨平台 Linux 容器化部署 | Docker Compose 三容器架構 |
| 資料庫 schema 擴充海事業務欄位 | MySQL schema migration |
| 六個月模擬值勤資料生成 | Python + NumPy 機率模型 |
| 資料清洗與統計分析 | Pandas |
| 視覺化圖表產出 | Matplotlib / Seaborn |
| 互動式分析儀表板 | Gradio |
| PHP 前端整合顯示分析結果 | Named volume 共享 |

---

## 二、資料集說明

### 2.1 資料來源

本專題使用自行生成之模擬值勤資料，以 Python 腳本（`src/analysis/generate_mock_data.py`）依海事排班邏輯產生，確保欄位組合的業務合理性。

| 資料表 | 筆數 | 說明 |
|--------|------|------|
| `users` | 13 筆 | 管理員 3 位、員工 10 位 |
| `attendance` | 約 1,000 筆 | 六個月值勤記錄（2025-11 至 2026-04） |
| `leaves` | 約 80 筆 | 請假申請記錄 |

### 2.2 資料欄位說明

**attendance 表**（本學期擴充後）：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `att_id` | INT PK | 流水號 |
| `user_id` | INT FK | 值班人員 |
| `work_date` | DATE | 值班日期 |
| `check_in` | DATETIME | 上勤時間（07:00–09:00） |
| `check_out` | DATETIME | 下勤時間（依海況調整） |
| `status` | ENUM | open / done |
| `duty_zone` | ENUM | **港口 / 近海 / 外海**（本學期新增） |
| `sea_state` | ENUM | **平靜 / 輕浪 / 中浪 / 大浪**（本學期新增） |
| `vessel_id` | VARCHAR(20) | **船艦編號 MAR-001 ~ MAR-008**（本學期新增） |

### 2.3 模擬資料機率模型

海域出勤機率：港口 35%、近海 40%、外海 25%

各海域海況機率分布：

| 海況 | 港口 | 近海 | 外海 |
|------|------|------|------|
| 平靜 | 70% | 40% | 15% |
| 輕浪 | 25% | 35% | 30% |
| 中浪 |  4% | 20% | 35% |
| 大浪 |  1% |  5% | 20% |

大浪天氣下提前下勤 100 分鐘，模擬現實海象對勤務時數之影響。

### 2.4 資料品質

- 缺失值：模擬資料生成時確保關鍵欄位完整；清洗階段進一步移除 null 記錄
- 異常值：值勤時數過濾條件為 4 ≤ hours ≤ 14，共移除比例 < 1%
- 一致性：`uq_user_date` 唯一約束確保同人同日僅一筆記錄

---

## 三、技術架構

### 3.1 系統架構圖

```
使用者瀏覽器
     │
     ├─── http://localhost:8080 ──── web 容器（php:8.2-apache）
     │                                    │  src/app/*.php
     │                                    │  analysis_output/ (volume)
     │
     └─── http://localhost:7860 ──── analysis 容器（python:3.11）
                                          │  src/analysis/app.py (Gradio)
                                          │  src/analysis/analysis.py
                                          │  analysis_output/ (volume)

兩容器均透過 Docker 內部網路連接：

     db 容器（mysql:8.0）
          │  maritime_duty 資料庫
          │  db_data volume（資料持久化）
          └──── 初始化：src/app/schema.sql
```

### 3.2 技術選型說明

| 層次 | 技術 | 選用原因 |
|------|------|---------|
| 前端 | PHP 8.2 + Apache | 延用上學期成果，降低重寫成本 |
| 資料庫 | MySQL 8.0 | 既有 schema 相容，生態完整 |
| 分析 | Python 3.11 + Pandas | 課程必要技術，資料處理能力強 |
| 視覺化 | Matplotlib + Seaborn | 課程必要技術，靜態圖品質佳 |
| 互動介面 | Gradio | 快速建立 ML/分析 demo，port 7860 |
| 容器化 | Docker Compose | 單指令啟動三服務，跨平台一致性 |
| 版本控制 | Git / GitHub | 課程必要技術 |

### 3.3 容器間通訊

- `web` 與 `analysis` 皆以 `DB_HOST=db` 連接同一 MySQL 實例
- 分析圖表透過 named volume `analysis_output` 從 Python 容器傳至 PHP 容器
- 所有連線憑證以環境變數（`.env` 檔）注入，不寫死於程式碼

### 3.4 使用技術清單

| 技術 | 類型 | 應用位置 |
|------|------|---------|
| Python + Pandas | 必要 | `analysis.py` 資料清洗與統計 |
| Matplotlib / Seaborn | 必要 | `analysis.py` 七張圖表 |
| Docker / Docker Compose | 必要 | `docker/` 三容器編排 |
| Git / GitHub | 必要 | commit 紀錄、PR 管理 |
| MySQL 8.0 | 選擇性 | 值勤資料持久化 |
| Apache + PHP 8.2 | 選擇性 | 前端操作介面 |
| Gradio | 選擇性 | 互動分析儀表板 |

---

## 四、資料分析過程

### 4.1 資料清洗

清洗邏輯位於 `src/analysis/analysis.py` 的 `_clean()` 函式，分三步驟執行：

**步驟一：缺失值移除**
```python
att = att.dropna(subset=["check_in", "check_out", "duty_zone", "sea_state", "vessel_id"])
```
確保所有分析用關鍵欄位均有值。

**步驟二：值勤時數計算與過濾**
```python
att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600
att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]
```
過濾不合理記錄：< 4 小時視為未完整打卡，> 14 小時視為資料異常。

**步驟三：衍生欄位建立**
```python
att["month_str"] = att["work_date"].dt.strftime("%Y-%m")
```
供後續月度分組分析使用。

### 4.2 統計分析

以 Pandas 進行多維度分組統計：

| 分析維度 | 方法 | 主要洞察 |
|---------|------|---------|
| 月度值勤量 | `groupby("month_str").size()` | 各月人力投入趨勢 |
| 海域分布 | `value_counts()` | 近海值勤最頻繁（約 40%）|
| 海域 × 海況 | `groupby(["duty_zone","sea_state"]).size().unstack()` | 外海大浪比例顯著高於港口 |
| 船艦出勤 | `groupby("vessel_id").size()` | 各船均勻輪替，無明顯過載 |
| 海況與時數 | `boxplot(x="sea_state", y="hours")` | 大浪時中位數時數較平靜低約 1.5h |
| 請假趨勢 | `groupby(["month_str","leave_type"]).size()` | 事假比例最高，冬季病假略增 |

### 4.3 視覺化

共產出七張圖表，輸出至 `analysis_output/` 共用 volume：

| 圖檔 | 圖表類型 | 說明 |
|------|---------|------|
| `monthly_trend.png` | 折線圖 + 填色 | 月度值勤人次趨勢，呈現季節性波動 |
| `zone_bar.png` | 長條圖 | 三海域值勤次數比較 |
| `zone_sea_stacked.png` | 堆疊長條圖 | 各海域內部海況組成，外海大浪佔比最高 |
| `vessel_count.png` | 水平長條圖 | 八艘船艦出勤次數，評估是否均衡輪替 |
| `hours_boxplot.png` | 箱型圖 | 四種海況下值勤時數分布，驗證大浪縮班假設 |
| `person_heatmap.png` | 熱力圖 | 人員 × 月份出勤天數矩陣，快速識別出勤不規律者 |
| `leave_trend.png` | 分組長條圖 | 每月各假別核准件數，供人力規劃參考 |

---

## 五、互動式分析應用（Gradio）

`src/analysis/app.py` 以 Gradio Blocks API 建立互動式分析介面，監聽 port 7860。

### 5.1 功能說明

使用者可透過以下篩選條件即時產生客製化圖表：

- **日期區間**：輸入開始／結束日期，限縮分析時間範圍
- **值勤海域**：勾選港口、近海、外海（可多選）
- **船艦篩選**：從 DB 動態載入船艦清單，支援多選

點擊「執行分析」後，`generate_charts()` 依篩選條件動態組合 SQL WHERE 子句查詢 MySQL，重新產生圖表後以網格方式顯示。

### 5.2 技術設計重點

- `analysis.py` 模組化為可呼叫函式，`app.py` 直接 import 使用，避免程式碼重複
- 篩選在 SQL 層執行（非 Python 層過濾），降低大資料量下的記憶體消耗
- 篩選結果存為 `filtered_*.png`，不覆蓋全覽圖表，PHP 儀表板持續可用

---

## 六、Docker 部署

### 6.1 目錄結構

```
docker/
├── docker-compose.yml      # 三容器編排
├── web/
│   └── Dockerfile          # php:8.2-apache + mysqli/pdo_mysql
└── analysis/
    └── Dockerfile          # python:3.11-slim + fonts-noto-cjk
```

### 6.2 容器規格

| 容器 | 基底映像 | Port | 主要 Volume |
|------|---------|------|------------|
| web | php:8.2-apache | 8080→80 | `src/app/` 掛載為 web root |
| db | mysql:8.0 | 內網 | `db_data` 持久化資料 |
| analysis | python:3.11-slim | 7860→7860 | `src/analysis/` 掛載為 `/app` |

分析圖表透過 named volume `analysis_output` 跨容器共用：
- analysis 容器寫入 `/app/output/`
- web 容器讀取 `/var/www/html/analysis_output/`

### 6.3 部署步驟

```bash
# 1. 設定環境變數
cp .env.example .env
# 編輯 .env，填入資料庫密碼

# 2. 啟動所有服務
cd docker
docker compose up --build

# 3. 初始化模擬資料（首次執行）
docker compose run analysis python generate_mock_data.py

# 4. 產生分析圖表
docker compose run analysis python analysis.py

# 5. 存取服務
# PHP 系統：http://localhost:8080
# Gradio 互動介面：http://localhost:7860
```

### 6.4 安全設計

- 資料庫連線憑證全程以環境變數傳遞，不寫入程式碼
- `.env` 已加入 `.gitignore`，不推送至 GitHub
- MySQL 使用非 root 帳號（`DB_USER`）連線應用程式
- PHP 透過 PDO prepared statement 防範 SQL Injection

---

## 七、成果展示

### 7.1 PHP 系統功能

| 功能頁面 | 說明 | 可用角色 |
|---------|------|---------|
| `login.php` | 帳號密碼登入，session 管理 | 全部 |
| `punch.php` | 上下勤打卡，顯示當日狀態 | 全部 |
| `records.php` | 個人值勤歷史查詢 | 全部 |
| `leave.php` | 請假申請（起訖日、假別、事由）| 全部 |
| `admin_status.php` | 全員值勤總覽，可依日期篩選 | 管理員以上 |
| `admin_leave.php` | 請假審核（核准／拒絕）| 管理員以上 |
| `admin_users.php` | 帳號管理、新增停用 | 管理員以上 |
| `admin_export.php` | 值勤記錄 CSV 匯出 | 管理員以上 |
| `admin_dashboard.php` | 分析圖表儀表板 | 管理員以上 |

### 7.2 預設測試帳號

| 帳號 | 密碼（hash 已存入 DB） | 角色 |
|------|----------------------|------|
| boss1 | （見 schema.sql）| 老闆 |
| admin1 | （見 schema.sql）| 管理員 |
| em1 | （見 schema.sql）| 員工 |
| chen_wei 等 10 人 | maritime2025 | 員工/管理員 |

### 7.3 分析圖表洞察摘要

- **月度趨勢**：值勤量冬季（11–12月）略低，春季（3–4月）回升，符合海事作業季節性
- **海域分布**：近海 40% > 港口 35% > 外海 25%，反映近岸巡邏為主要任務
- **海況影響**：外海大浪比例達 20%，箱型圖確認大浪天值勤時數中位數較平靜天低約 1.5 小時
- **船艦輪替**：八艘船艦出勤次數標準差低，輪班制度執行均勻

---

## 八、分工說明

| 組員 | 負責項目 | 貢獻比例 |
|------|---------|---------|
| 黃宇平（組長）| 系統架構設計、Docker 容器化、PHP 系統 Linux 化、Schema 擴充、Python 模擬資料生成、Pandas 分析、Matplotlib/Seaborn 圖表、Gradio 互動介面、整合測試、文件統籌 | 主要實作 |
| 傅瀚鋌 | 模擬資料生成邏輯討論、報告章節撰寫協助 | 支援 |
| 曾紹喆 | 分析結果檢視與回饋、投影片內容協助 | 支援 |
| 劉家样 | 系統功能測試、Demo 流程配合 | 支援 |
| 李翊丞 | 文件校對、報告排版協助 | 支援 |
| 林秉賢 | 期末發表 Demo 配合、會議紀錄 | 支援 |

技術實作由組長集中執行，組員負責文件校對、功能測試、簡報配合等支援性工作。此分工安排已事先徵得授課教師同意。

---

## 九、心得與建議

### 黃宇平（組長）

本學期最大的收穫是親身體驗從「可以跑」到「可以部署」的距離。上學期的 PHP 系統在 XAMPP 上能動，但移植到 Linux 容器時才發現連線設定、路徑、字型等細節都需要重新處理。Docker Compose 的三容器架構讓各元件責任清楚，也讓我理解為何業界喜歡容器化。Python 分析端與 PHP 端透過 named volume 共享圖表這個設計，簡單但有效，是這次最滿意的架構決策。

### 傅瀚鋌

參與模擬資料的邏輯討論，讓我了解真實資料的機率分布設計比直覺想像的複雜。港口與外海的海況分布差異若不合理，後續分析就會失去意義。這讓我更能體會資料品質對分析結果的根本影響。

### 曾紹喆

看到最後的分析圖表，尤其是箱型圖顯示大浪天確實縮短值勤時數，感覺資料「說話」了。這讓我理解視覺化不只是呈現，而是驗證假設的工具。

### 劉家样

在測試功能時發現一些邊界情況，例如請假日期跨月的顯示問題，以及尚未執行分析時儀表板的引導提示設計。這讓我體會到使用者視角在測試中的重要性。

### 李翊丞

校對報告的過程讓我更清楚整個系統的脈絡。原本以為只是打卡系統，讀完報告才發現從 Docker 部署到資料分析有相當完整的技術鏈。文件的重要性不亞於程式碼本身。

### 林秉賢

參與 Demo 演練，協助確認從 `docker compose up` 到操作 PHP 系統再到 Gradio 分析的完整流程是否順暢。容器起動順序（db healthcheck 後才啟動 web 和 analysis）這個設計細節讓 Demo 穩定很多。

---

## 十、參考資料

1. Docker 官方文件 — Compose file reference  
   https://docs.docker.com/compose/compose-file/

2. PHP: PDO — Manual  
   https://www.php.net/manual/en/book.pdo.php

3. pandas documentation  
   https://pandas.pydata.org/docs/

4. Seaborn: statistical data visualization  
   https://seaborn.pydata.org/

5. Gradio Documentation  
   https://www.gradio.app/docs/

6. MySQL 8.0 Reference Manual  
   https://dev.mysql.com/doc/refman/8.0/en/

7. Matplotlib Documentation  
   https://matplotlib.org/stable/contents.html

8. 中央氣象署海洋觀測資料  
   https://ocean.cwa.gov.tw

9. php:8.2-apache Docker Hub  
   https://hub.docker.com/_/php

10. python:3.11-slim Docker Hub  
    https://hub.docker.com/_/python
