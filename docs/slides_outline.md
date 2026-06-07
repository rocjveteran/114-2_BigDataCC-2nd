# 投影片大綱
# 海勤人力資源與作業安全決策系統
# 114-2 巨量資料與雲端運算 第 2 組

> 定位：這是一套「用海象做人力決策」的管理系統，海象只是輸入訊號之一，
> 真正的輸出是**人員疲勞、工時公平、船艦可用性與明日值勤班表**。

---

## Slide 1｜封面

**海勤人力資源與作業安全決策系統**
*海象感知智慧排班 · 海事勤務雲端管理平台*
114-2 巨量資料與雲端運算 ── 第 2 組
黃宇平 · 傅瀚鋌 · 曾紹喆 · 劉家样 · 李翊丞 · 林秉賢

> 別人把海象畫成圖，我們把海象變成「明天誰上哪艘船」。

---

## Slide 2｜我們與第 5 組（海象資料視覺化）不同在哪

| | 第 5 組 | 第 2 組（我們） |
|--|---------|--------------|
| 資料主角 | 海象觀測值 | 值勤紀錄 × 人員 × 船艦（海象只是輸入） |
| 核心問題 | 海象怎麼分析、怎麼畫？ | 海象惡劣時，**明天該派誰、上哪艘船**？ |
| 系統本質 | 分析 / 視覺化平台 | 含打卡 / 請假 / 帳號的**決策支援系統（DSS）** |
| 招牌輸出 | 海象趨勢圖 | **自動排班引擎 → 明日值勤班表** |

**他們做不到、我們才有的維度**（皆需人員/船艦資料，純海象資料無法產出）：
- 人員疲勞指數（連續值勤、休息間隔）
- 工時公平性 Gini + Lorenz 曲線
- 船艦可用性與維護里程
- 自動排班引擎（具名輸出明日班表）

**全班唯一把海象接進人力資源排班決策的管理系統。**

---

## Slide 3｜問題與動機

上學期成果 → 三項不足

| 問題 | 本學期解法 |
|------|-----------|
| 只能在 Windows XAMPP 執行 | Docker 三容器，一指令啟動 |
| 只記錄、不決策 | 排班引擎 + 21 張分析圖 + ML 預測 |
| 通用打卡，無海事特性 | duty_zone / sea_state / vessel_id + CWA 即時海象 |

---

## Slide 4｜系統架構

```
瀏覽器 :8080          瀏覽器 :7860
    │                      │
  web 容器              analysis 容器
php:8.2-apache          python:3.11
    │                      │
    └──── analysis_output volume ────┘
               │           （recommendations.json / 圖表 / duty_map.html / 模型）
           db 容器
          mysql:8.0   ← attendance / leaves / users / sea_observations
```

三容器 · 共用網路 · Named Volume 傳遞班表與圖表

---

## Slide 5｜技術清單

| 必要技術 | ✅ |
|---------|---|
| Python + Pandas | 資料清洗 / 統計分析 / 排班引擎 |
| Matplotlib / Seaborn | 21 張視覺化圖表 |
| Docker 容器化 | docker-compose 三容器 |
| Git / GitHub | Commit 紀錄 / PR / CI |

| 選擇性技術 | ✅ |
|-----------|---|
| MySQL 資料庫 | 四張資料表（含 sea_observations） |
| Apache + PHP | 完整業務系統 + 排班決策頁 |
| scikit-learn | RandomForest 海況預測 + joblib 落地 |
| Folium | 互動海域地圖 |
| Gradio | 即時篩選互動分析 |
| 中央氣象署開放資料 | CWA 浮標海象（無金鑰自動模擬備援） |

---

## Slide 6｜資料設計

**attendance 表擴充欄位**

```
duty_zone  ENUM('港口','近海','外海')
sea_state  ENUM('平靜','輕浪','中浪','大浪')
vessel_id  VARCHAR(20)   -- MAR-001 ~ MAR-008
```

**sea_observations 表（CWA 即時海象）**

```
station_id / obs_date / wave_height / sea_temp / sea_state / data_source
```

- 外海大浪機率 20%（vs 港口 1%）、大浪天提前下勤
- 共 13 人 × 6 個月 ≈ 1,200 筆值勤 + 4 浮標站海象觀測

---

## Slide 7｜資料清洗

```python
att = att.dropna(subset=["check_in","check_out","duty_zone","sea_state","vessel_id"])
att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600
att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]
```

清洗前後差異 < 1%，資料品質佳

---

## Slide 8｜⭐ 核心：自動排班引擎（Demo 重點）

**Demo 截圖：PHP「明日值勤排班」頁**

```
輸入                            →   引擎   →   輸出
─────────────────────────────────────────────────
明日惡劣海況機率（ML/Markov）          明日值勤班表
人員疲勞指數                          ├ 港口 N 人（誰、哪艘船）
人員外海暴露率（公平輪換）             ├ 近海 N 人
船艦可用性（維護里程）                └ 外海 N 人（惡劣海況自動縮減）
                                     + 建議輪休人員 + 維護中船艦
```

**決策邏輯**：海況惡劣 → 縮減外海員額；低疲勞低暴露者輪派外海；
過勞者配置港口輕負荷；維護中船艦自動排除。

`build_schedule()` → `recommendations.json` → PHP + Gradio 雙呈現

---

## Slide 9｜人力資源分析（第 5 組做不出來）

**Demo 截圖：分析儀表板「人力資源決策」區**

| 圖表 / 輸出 | 關鍵發現 |
|------|---------|
| `fatigue.png` | 疲勞指數排行，紅色為高疲勞（建議輪休） |
| `fairness_lorenz.png` | 工時公平性 Lorenz 曲線 + Gini 係數 |
| `vessel_availability.png` | 船艦維護里程，紅色為需維護、排班自動排除 |
| 人員外海暴露排名 | 依外海比例排序，輔助輪換 |

---

## Slide 10｜海象智慧分析（輸入端）

**Demo 截圖：互動海域地圖 + 預測圖**

| 圖表 | 關鍵發現 |
|------|---------|
| `duty_map.html` | **Folium 互動地圖**：三海域風險 + 船艦 + CWA 浮標站 |
| `markov_heatmap.png` | Markov 矩陣：海況轉移機率 + 7 天預測 |
| `feature_importance.png` | RandomForest 預測明日惡劣海況（含準確率/AUC） |
| `regression_coef.png` | OLS 工時建模：R² ≈ 0.35 |
| `crew_clusters.png` | K-means 人員型態分群 |

---

## Slide 11｜Gradio 互動介面

**Demo 截圖**

篩選條件 → 執行分析 → 即時更新所有輸出

- 「勤務決策建議」tab：明日班表 + 即時海況 + 警示 + 暴露排名
- 「人力資源決策」tab：疲勞 / 公平 / 船艦 / 海域圖
- 「預測與建模」tab：時序預測 / Markov / RandomForest 特徵重要度
- 日期 / 海域 / 船艦三維篩選

---

## Slide 12｜PHP 系統功能

**Demo 截圖**

- 員工：登入（粒子波動畫）/ 打卡 / 請假 / 即時海象橫幅 + 個人疲勞卡
- 管理員：**明日排班**（旗艦決策頁）、勤務總覽、請假審核、帳號管理
- 管理員：**分析儀表板** → 排班摘要 + Folium 地圖 + 21 張圖

---

## Slide 13｜Docker 部署 Demo

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

## Slide 14｜GitHub 管理

```
[docker]    建立三容器 docker-compose 配置
[app]       置入 PHP 系統 + 明日排班決策頁
[data]      模擬值勤資料 + CWA 海象管線
[analysis]  人力資源與排班決策引擎 + 21 張圖 + ML 模型
[docs]      期末報告與投影片
```

PR 流程：feature branch → main · GitHub Actions CI（33 tests）

---

## Slide 15｜結語與未來展望

**本學期達成**
- 定位：海象視覺化 → **海勤人力資源與作業安全決策系統** ✅
- **自動排班引擎**（全班唯一，具名輸出明日班表）✅
- 人員疲勞指數 / 工時公平性 Lorenz / 船艦可用性 ✅
- scikit-learn RandomForest 海況預測 + Markov 轉移 ✅
- Folium 互動海域地圖 ✅
- CWA 即時海象資料管線 ✅
- 跨平台容器化部署 + GitHub Actions CI（33 tests）✅

**未來可延伸**
- 接入 CWA 即時海象 API（已備金鑰機制）
- 線性規劃 / 整數規劃強化排班最佳化
- 行動裝置現場打卡

---

*簡報製作建議工具：Google Slides / PowerPoint*
*圖表截圖請於 `docker compose up` 後執行 `python analysis.py` 取得*
