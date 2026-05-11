# 投影片大綱
# 海事勤務值勤雲端管理系統
# 114-2 巨量資料與雲端運算 第 2 組

---

## Slide 1｜封面

**海事勤務值勤雲端管理系統**
114-2 巨量資料與雲端運算 ── 第 2 組
黃宇平 · 傅瀚鋌 · 曾紹喆 · 劉家样 · 李翊丞 · 林秉賢

---

## Slide 2｜問題與動機

上學期成果 → 三項不足

| 問題 | 本學期解法 |
|------|-----------|
| 只能在 Windows XAMPP 執行 | Docker 三容器，一指令啟動 |
| 只記錄、不分析 | Pandas + Seaborn 七張圖 |
| 通用打卡，無海事特性 | duty_zone / sea_state / vessel_id |

---

## Slide 3｜系統架構

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

## Slide 4｜技術清單

| 必要技術 | ✅ |
|---------|---|
| Python + Pandas | 資料清洗 / 統計分析 |
| Matplotlib / Seaborn | 七張視覺化圖表 |
| Docker 容器化 | docker-compose 三容器 |
| Git / GitHub | Commit 紀錄 / PR |

| 選擇性技術 | ✅ |
|-----------|---|
| MySQL 資料庫 | 三張資料表 |
| Apache + PHP | 前端操作介面 |
| Gradio 互動介面 | 即時篩選分析 |

---

## Slide 5｜資料設計

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

## Slide 6｜資料清洗

```python
# 移除 null 欄位
att = att.dropna(subset=["check_in","check_out","duty_zone","sea_state","vessel_id"])

# 過濾不合理時數
att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600
att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]
```

清洗前後差異 < 1%，資料品質佳

---

## Slide 7｜分析洞察（圖表展示）

**放入圖表截圖**

- `zone_sea_stacked.png`：外海大浪佔比 20%，遠高於港口
- `hours_boxplot.png`：大浪天值勤時數中位數低 ~1.5h
- `person_heatmap.png`：人員出勤熱力圖，快速識別異常

---

## Slide 8｜Gradio 互動介面

**Demo 截圖**

篩選條件 → 執行分析 → 即時圖表更新

- 日期區間篩選
- 海域多選
- 船艦多選（從 DB 動態載入）

---

## Slide 9｜PHP 系統功能

**Demo 截圖**

- 登入 / 打卡 / 請假申請
- 管理員：值勤總覽、請假審核、帳號管理
- 管理員：**分析儀表板**（嵌入 Python 圖表）

---

## Slide 10｜Docker 部署 Demo

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

## Slide 11｜GitHub 管理

Commit 紀錄（依前綴分類）：

```
[docker]    建立三容器 docker-compose 配置
[app]       置入 PHP 系統並完成 Linux 化改造
[data]      新增模擬值勤資料生成腳本
[analysis]  新增資料清洗、統計分析與七張視覺化圖表
[app]       整合 Gradio 互動介面與 PHP 分析儀表板
[docs]      期末報告與投影片大綱
```

PR 流程：feature branch → main

---

## Slide 12｜結語與未來展望

**本學期達成**
- 跨平台容器化部署 ✅
- 海事 schema 擴充 ✅
- 7 張分析圖表 ✅
- Gradio 互動儀表板 ✅

**未來可延伸**
- 接入中央氣象署即時海象 API
- Keras 預測模型（值勤人力需求預測）
- AIS 即時船位資料整合
- 行動裝置介面

---

*簡報製作建議工具：Google Slides / PowerPoint*
*圖表截圖請於 `docker compose up` 後執行 `python analysis.py` 取得*
