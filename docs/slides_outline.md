# 投影片大綱
# 海象感知智慧排班與勤務決策平台
# 114-2 巨量資料與雲端運算 第 2 組

---

## Slide 1｜封面

**海象感知智慧排班與勤務決策平台**
*海事勤務值勤雲端管理系統*
114-2 巨量資料與雲端運算 ── 第 2 組
黃宇平 · 傅瀚鋌 · 曾紹喆 · 劉家样 · 李翊丞 · 林秉賢

> 別人分析海象，我們用海象做人力決策。

---

## Slide 2｜我們與第 5 組不同在哪

| | 第 5 組 | 第 2 組（我們） |
|--|---------|--------------|
| 核心問題 | 海象資料怎麼分析？ | 海象怎麼影響人力決策？ |
| 資料主角 | 氣象觀測值 | 值勤紀錄 × 海象欄位 |
| 輸出 | 海象趨勢圖表 | 排班建議 + 工時迴歸模型 |
| 系統 | 分析平台 | 含打卡 / 請假 / 管理的完整業務系統 |

**全班唯一把海象資料接進值勤排班決策的管理系統。**

---

## Slide 3｜問題與動機

上學期成果 → 三項不足

| 問題 | 本學期解法 |
|------|-----------|
| 只能在 Windows XAMPP 執行 | Docker 三容器，一指令啟動 |
| 只記錄、不分析 | Pandas + Seaborn 15 張圖 |
| 通用打卡，無海事特性 | duty_zone / sea_state / vessel_id |

---

## Slide 4｜系統架構

```
瀏覽器 :8080          瀏覽器 :7860
    │                      │
  web 容器              analysis 容器
php:8.2-apache          python:3.11
    │                      │
    └──── analysis_output volume ────┘
               │
           db 容器
          mysql:8.0
```

三容器 · 共用網路 · Named Volume 傳遞圖表

---

## Slide 5｜技術清單

| 必要技術 | ✅ |
|---------|---|
| Python + Pandas | 資料清洗 / 統計分析 |
| Matplotlib / Seaborn | 15 張視覺化圖表 |
| Docker 容器化 | docker-compose 三容器 |
| Git / GitHub | Commit 紀錄 / PR |

| 選擇性技術 | ✅ |
|-----------|---|
| MySQL 資料庫 | 三張資料表 |
| Apache + PHP | 前端操作介面 |
| Gradio 互動介面 | 即時篩選分析 |

---

## Slide 6｜資料設計

**attendance 表擴充欄位**

```
duty_zone  ENUM('港口','近海','外海')
sea_state  ENUM('平靜','輕浪','中浪','大浪')
vessel_id  VARCHAR(20)   -- MAR-001 ~ MAR-008
```

**模擬資料機率模型**
- 外海大浪機率 20%（vs 港口 1%）
- 大浪天提前下勤 100 分鐘
- 共 13 人 × 6 個月 ≈ 1,000 筆值勤記錄

---

## Slide 7｜資料清洗

```python
# 移除 null 欄位
att = att.dropna(subset=["check_in","check_out","duty_zone","sea_state","vessel_id"])

# 過濾不合理時數
att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600
att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]
```

清洗前後差異 < 1%，資料品質佳

---

## Slide 8｜分析洞察（圖表展示）

**以下三張為 Demo 重點截圖**

| 圖表 | 關鍵發現 |
|------|---------|
| `zone_sea_stacked.png` | 外海大浪比例 20%，是港口的 20 倍 |
| `hours_boxplot.png` | 大浪天工時中位數低 1.5 h（ANOVA p < 0.05）|
| `forecast_duty.png` | 線性外推未來 4 週，含 95% 預測區間 |
| `regression_coef.png` | OLS 建模：R² ≈ 0.35，上工時刻為最大負向因子 |
| `crew_clusters.png` | K-means 三群：高外海型 / 港口值守型 / 均衡型 |

---

## Slide 9｜勤務決策建議（核心差異化功能）

**Demo 截圖：PHP 儀表板「勤務決策建議」看板 + Gradio 決策建議 tab**

系統以近 30 天資料自動計算：

| 輸出 | 說明 |
|------|------|
| 警示訊息 | 大浪比例超閾值 / 外海×大浪組合 / 超時值勤（分 ok/info/warn/err）|
| 海域風險表 | 各海域次數、平均工時、大浪%，超過 20% 標紅 |
| 人員暴露排名 | 依外海值勤比例排序，輔助輪換安排（Top 8）|
| 標題摘要 | 一句話自動產生的決策建議語 |

`compute_recommendations()` → `recommendations.json` → PHP + Gradio 雙管道呈現

---

## Slide 10｜Gradio 互動介面

**Demo 截圖**

篩選條件 → 執行分析 → 即時更新所有輸出

- 「勤務決策建議」tab（首位）：警示 + 風險表 + 暴露排名
- 「時序趨勢」「預測與建模」「海域×海況」「資源調度」「異常診斷」共 5 個圖表 tab
- 日期 / 海域 / 船艦三維篩選，篩選結果存 `filtered_*.png` 不蓋掉全覽

---

## Slide 11｜PHP 系統功能

**Demo 截圖**

- 登入（粒子波動畫） / 值勤打卡 / 請假申請
- 管理員：值勤總覽、請假審核、帳號管理
- 管理員：**分析儀表板** → 勤務決策建議 + 15 張圖表

---

## Slide 12｜Docker 部署 Demo

```bash
cp .env.example .env
cd docker
docker compose up --build
```

↓ 約 60 秒後

- http://localhost:8080  ← PHP 系統
- http://localhost:7860  ← Gradio 分析

**一指令完成部署，跨平台可執行**

---

## Slide 13｜GitHub 管理

Commit 紀錄（依前綴分類）：

```
[docker]    建立三容器 docker-compose 配置
[app]       置入 PHP 系統並完成 Linux 化改造
[data]      新增模擬值勤資料生成腳本
[analysis]  新增資料清洗、統計分析與 15 張視覺化圖表
[app]       整合 Gradio 互動介面與 PHP 分析儀表板
[docs]      期末報告與投影片大綱
```

PR 流程：feature branch → main

---

## Slide 14｜結語與未來展望

**本學期達成**
- 跨平台容器化部署 ✅
- 海事 schema 擴充（duty_zone / sea_state / vessel_id）✅
- 15 張分析圖表（含預測、迴歸、分群）✅
- 工時迴歸建模 + 時序預測 ✅
- 勤務決策建議模組（全班唯一）✅
- Gradio 互動儀表板 ✅
- GitHub Actions CI（21 tests）✅

**未來可延伸**
- 接入中央氣象署即時海象 API
- Keras 預測模型（值勤人力需求預測）
- AIS 即時船位資料整合
- 行動裝置介面

---

*簡報製作建議工具：Google Slides / PowerPoint*
*圖表截圖請於 `docker compose up` 後執行 `python analysis.py` 取得*
