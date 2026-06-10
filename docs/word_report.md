<!-- 本檔為期末 Word 報告底稿，章節結構完全對齊老師範本（六章節）。
     繳交檔名：巨量資料與雲端運算技術_海勤人力資源與作業安全決策系統_黃宇平_傅瀚鋌_曾紹喆_劉家样_李翊丞_林秉賢.docx
     圖 1–3 在 docs/figures/，研究圖（21 張）執行 docker compose up 後於 analysis_output/ 取得。
     〔執行後填入〕標記處：跑完分析後以 recommendations.json 實際數值取代。 -->

# 巨量資料與雲端運算技術 期末報告

## 海勤人力資源與作業安全決策系統
### —— 海象感知智慧排班 · 海事勤務雲端管理平台

國立高雄科技大學 海事資訊科技系

| 身分 | 姓名 / 學號 |
|------|------------|
| 組長 | 黃宇平 / C112181108 |
| 組員 | 傅瀚鋌 / C112181112 |
| 組員 | 曾紹喆 / C112181182 |
| 組員 | 劉家样 / C111181141 |
| 組員 | 李翊丞 / C111181134 |
| 組員 | 林秉賢 / C112181148 |

指導老師：張珀銀 老師

---

## (一) 摘要

本研究將上學期完成、僅能運行於 Windows XAMPP 之 PHP + MySQL 值勤管理雛形，改造為 Linux 雲端容器化之「海勤人力資源與作業安全決策系統」。系統採 Docker Compose 三容器架構（Apache/PHP 前端、MySQL 資料庫、Python 分析服務），以單一指令完成跨平台部署；以 Python 生成約 1,200 筆含海域、海況、船艦欄位之六個月模擬值勤資料，並串接中央氣象署（CWA）浮標海象觀測約 720 筆。分析端以 Pandas 完成清洗與統計檢定，產出 21 張 Matplotlib/Seaborn 視覺化圖表，以 scikit-learn RandomForest 預測明日惡劣海況，再由自動排班引擎綜合海況風險、人員疲勞指數、外海暴露公平性與船艦可用性四項輸入，自動產出明日三海域具名值勤班表。成果以 PHP 決策頁、Gradio 互動儀表板與 Folium 互動海域地圖呈現，全程以 GitHub 管理並通過 33 項自動化測試之 CI 驗證。本系統將海象由「視覺化對象」轉變為「人力決策輸入」，展示巨量資料與雲端運算技術於海事人力資源管理之實務應用。

## (二) 研究動機與研究問題

### 研究動機

本組上學期完成之海事勤務值勤管理系統具備登入、打卡、請假與三層級權限功能，然其僅為「紀錄工具」而非「決策工具」。海勤值勤具高風險特性：海況惡劣時外海作業風險陡增，人員連續值勤造成之疲勞累積為海事事故重要肇因（IMO, 2019）。管理者實務上最需要的不是更多報表，而是「明天該派誰、上哪艘船」的直接答案。同時，原系統綁定 Windows XAMPP，與雲端時代之部署型態脫節。本研究因此以容器化、資料分析與決策自動化三軸，將舊系統升級為決策支援系統（DSS）。

### 研究問題

1. 原系統部署綁定 Windows + XAMPP，移轉至任一新主機須手動安裝設定 Apache、PHP、MySQL 至少 3 套軟體，環境組態不可重現，亦無法快速從異常中恢復服務。
2. 系統累積約 1,200 筆值勤紀錄，卻產出 0 張分析圖表：管理層無法掌握工時負荷分布、海況與值勤量之關聯，更無任何預測能力。
3. 排班全憑人工經驗，未納入海況風險、人員疲勞、工時公平與船艦維護等至少 4 項決策因子，惡劣海況時段無法系統性縮減外海派遣員額。

### 研究目的

1. 以 Docker Compose 建構 web、db、analysis 三容器架構，於 Linux 環境以單一指令（`docker compose up`）完成全系統部署，啟動時間 60 秒內，容器異常時可即時重建恢復服務。
2. 以 Pandas 清洗約 1,200 筆值勤與約 720 筆 CWA 浮標海象資料，產出 21 張涵蓋描述統計、假設檢定（ANOVA、卡方）、時間序列預測、Markov 海況轉移與機器學習之分析圖表，並提供 Gradio 互動式儀表板。
3. 建立自動排班引擎 `build_schedule()`：綜合 RandomForest 明日海況預測、人員疲勞指數（0–100）、外海暴露公平輪換與船艦可用性共 4 項輸入，自動產出明日港口／近海／外海三海域具名班表，並附建議輪休與船艦維護清單。

## (三) 文獻探討與回顧

**容器化與可重現部署。** Merkel（2014）指出 Docker 以輕量級 Linux 容器封裝應用及其依賴，使開發、測試與生產環境保持一致；Boettiger（2015）進一步論證容器化對「可重現運算」之價值——任何人在任何主機以相同映像即可重現相同服務。本研究據此以 Docker Compose 編排三容器，解決原系統綁定單一 Windows 主機、環境不可重現之問題。

**海勤人員疲勞與作業安全。** Smith、Allen 與 Wadsworth（2006）之 Cardiff 海員疲勞研究計畫證實，連續值勤天數與不足之休息間隔顯著提高海上人為失誤風險；國際海事組織（IMO, 2019）之疲勞管理指引（MSC.1/Circ.1598）亦要求營運者以系統化方法監測與管理船員疲勞。本研究將「連續值勤天數」與「近 7 日累積工時」量化為 0–100 之疲勞指數，作為排班引擎之硬性輸入，呼應上述文獻對疲勞管理制度化之要求。

**海況統計建模與預測。** Monbet、Ailliot 與 Prevosto（2007）系統性回顧風與海況時間序列之隨機模型，其中 Markov 鏈為描述海況狀態轉移之經典方法。機器學習方面，Breiman（2001）提出之隨機森林以多樹集成降低過度擬合，適合中小型結構化資料之分類任務。本研究同時採用兩者：以 Markov 轉移矩陣估計未來 7 日海況分布，並以 scikit-learn（Pedregosa et al., 2011）之 RandomForest 結合滯後特徵預測明日是否出現惡劣海況，兩種方法互為驗證。

**工時公平性度量。** 經濟學以 Lorenz 曲線與 Gini 係數衡量分配不均，Gini 係數介於 0（完全平等）至 1（完全不均）。本研究將其移植至工時分配場景：以各人員累積工時計算 Gini 係數並繪製 Lorenz 曲線，量化值勤負荷之公平程度，並以「外海暴露率」之相對排名驅動輪換建議，使排班公平性由主觀感受變為可監測指標。

**資料分析工具鏈。** 本研究之分析管線建構於 Python 生態系：Pandas（McKinney, 2010）負責資料清洗與聚合，Matplotlib（Hunter, 2007）與 Seaborn 負責統計視覺化，Gradio（Abid et al., 2019）提供無需前端開發即可部署之互動式機器學習介面。

## (四) 研究方法與步驟

### 系統架構

系統採三容器架構（圖 1）：web 容器（`php:8.2-apache`）承載 Linux 化改造後之 22 個 PHP 檔案，提供打卡、請假、權限管理與排班決策頁；db 容器（`mysql:8.0`）存放 users、attendance、leaves、sea_observations 四張資料表；analysis 容器（`python:3.11`）執行資料清洗、統計分析、機器學習與排班引擎。三容器共用 Docker 內部網路，分析產物（21 張 PNG、Folium 地圖、`recommendations.json`）經 named volume 交付 PHP 前端嵌入顯示。

> 【圖 1：三容器系統架構圖，docs/figures/fig1_architecture.png】

### 建置步驟說明

**A. 使用 Docker 建置 MySQL 資料庫服務。** 以官方 `mysql:8.0` 映像啟動，連線帳密經環境變數注入（`.env`），不寫死於程式碼。於上學期 attendance 表新增 `duty_zone`（港口/近海/外海）、`sea_state`（平靜/輕浪/中浪/大浪）、`vessel_id` 三個海事業務欄位，並新增 `sea_observations` 表存放 CWA 浮標逐日觀測。

**B. 使用 Docker 建置 Web 伺服器。** 以 `php:8.2-apache` 映像承載 PHP 系統，完成 Linux 化改造：路徑大小寫修正、字元集統一 utf8mb4、資料庫連線改為 `getenv()` 讀取環境變數。新增 `scheduler.php`（明日排班決策頁）、`api_status.php`（每 60 秒輪詢之即時艦上狀態 JSON 端點）與管理員分析儀表板。

**C. 使用 Docker 建置 Python 分析服務。** 以 `python:3.11` 映像執行資料管線（圖 2）：`generate_mock_data.py` 依輪班規則與海域—海況聯合機率生成約 1,200 筆值勤紀錄；`fetch_sea_data.py` 擷取 CWA 開放資料浮標觀測（無 API 金鑰時自動以季節性模型模擬備援，欄位 `data_source` 誠實標記來源）；`analysis.py` 完成清洗、21 張圖表、RandomForest 訓練與排班計算；Gradio 於 7860 埠提供互動分析。

> 【圖 2：資料流程圖，docs/figures/fig2_dataflow.png】

**D. 自動排班引擎。** 核心函式 `build_schedule()`（圖 3）依四條規則運作：①明日惡劣海況機率越高，外海員額自動越少（機率 ≥50% 時外海僅留 1 組）；②外海優先指派「低疲勞且低外海暴露」人員，兼顧安全與公平輪換；③高疲勞（過勞）人員配置港口輕負荷或建議輪休；④維護中船艦自動排除，每艦同時段僅指派一組人員，船艦不足時輸出 `vessel_limited` 警示。輸出統一寫入 `recommendations.json`，由 PHP 與 Gradio 雙端呈現。

> 【圖 3：排班決策引擎輸入—規則—輸出圖，docs/figures/fig3_engine.png】

**E. 資料清洗與品質控管。** 清洗規則如下，清洗前後資料量差異小於 1%：

```python
att = att.dropna(subset=["check_in","check_out","duty_zone","sea_state","vessel_id"])
att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600
att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]   # 剔除異常工時
```

**F. 版本控制與持續整合。** 全程以 Git/GitHub 管理，commit 訊息依 `[docker]`、`[app]`、`[data]`、`[analysis]`、`[docs]`、`[fix]` 分類；GitHub Actions 於每次推送自動執行 33 項 pytest 測試（涵蓋資料清洗、統計函式、疲勞/公平性/船艦可用性計算與排班引擎行為驗證）。

### 作者貢獻

表 1. 組員分工表

| 組員 | 負責項目 |
|------|---------|
| 黃宇平（組長） | 系統架構設計；Docker 三容器建置；PHP Linux 化（22 檔）；Schema 擴充；模擬資料與 CWA 海象管線；Pandas 分析與 21 張圖表；RandomForest 與排班引擎；Gradio 介面；CI 建置；整合測試；技術文件統籌 |
| 傅瀚鋌 | 海事業務知識（輪班制度、海域劃分）；資料欄位合理性審查；報告資料集章節初稿 |
| 曾紹喆 | 圖表洞察文字撰寫；投影片視覺設計與排版 |
| 劉家样 | 系統功能驗收測試（打卡、請假、管理介面邊界條件）；Demo 流程規劃與彩排 |
| 李翊丞 | 技術文件校對；參考文獻蒐集與格式整理 |
| 林秉賢 | 口頭報告稿件協調與時間掌控；Demo 現場操作；會議紀錄 |

## (五) 結果與結論

本節逐條回應研究目的：

**1. 容器化部署目標達成。** 系統於 Linux 環境以 `docker compose up` 單一指令完成三容器部署，實測約 60 秒內 web（:8080）與 Gradio（:7860）服務均可存取；容器異常時 `docker compose restart` 數秒內恢復服務，環境組態完全由 `docker-compose.yml` 與 `.env` 描述，任意主機可重現。

**2. 資料分析目標達成。** 完成約 1,200 筆值勤＋約 720 筆海象資料之清洗（損失率 <1%）與 21 張分析圖表，涵蓋：月度值勤趨勢、海域分布、海況×海域熱力圖、工時分布、ANOVA 與卡方檢定、時間序列預測、多元迴歸工時建模（R² = 0.778，可解釋約 78% 單次工時變異）、Markov 海況轉移矩陣與 7 日預測、K-means 人員分群、RandomForest 特徵重要度、人員疲勞排行、工時公平 Lorenz 曲線（Gini = 0.033，分配均勻）、船艦可用性與靜態海域風險地圖。假設檢定方面，ANOVA 證實海況顯著影響工時（F = 167.9，p < 0.0001），卡方檢定證實海域與海況顯著關聯（χ² = 331.0，df = 6，p < 0.0001）。RandomForest 於保留測試集達準確率 92.3%、AUC 0.713（訓練 116 筆、測試 39 筆）。Gradio 儀表板支援日期／海域／船艦三維篩選即時重算。

**3. 自動排班目標達成。** 排班引擎成功產出明日三海域具名班表（誰、哪海域、哪艘船），並附建議輪休名單、維護中船艦與可用艦不足警示；惡劣海況情境測試確認外海員額隨風險機率自動縮減。33 項自動化測試於 GitHub Actions 全數通過，驗證引擎之「不重複指派同艦」「過勞者不派外海」等決策約束。

**結論。** 本研究完成由「值勤紀錄工具」至「人力資源決策系統」之升級：海象在本系統中僅為輸入訊號，真正輸出為人員疲勞、工時公平、船艦可用性與自動產生之明日班表——此為純海象視覺化系統無法產出之決策維度。系統同時完整覆蓋課程必要技術（Python/Pandas、Matplotlib/Seaborn、Docker、Git/GitHub）與多項選擇性技術（MySQL、Apache+PHP、scikit-learn、Folium、Gradio、Jupyter、CWA 開放資料）。未來可延伸方向包括：接入 CWA 即時 API 金鑰以取得線上觀測（機制已內建）、以線性／整數規劃強化排班最佳化，以及行動裝置現場打卡。

## (六) 參考文獻

1. Merkel, D. (2014). Docker: Lightweight Linux containers for consistent development and deployment. *Linux Journal*, 2014(239).
2. Boettiger, C. (2015). An introduction to Docker for reproducible research. *ACM SIGOPS Operating Systems Review*, 49(1), 71–79.
3. Smith, A., Allen, P., & Wadsworth, E. (2006). *Seafarer fatigue: The Cardiff Research Programme*. Cardiff University.
4. International Maritime Organization. (2019). *Guidelines on fatigue* (MSC.1/Circ.1598). IMO.
5. Monbet, V., Ailliot, P., & Prevosto, M. (2007). Survey of stochastic models for wind and sea state time series. *Probabilistic Engineering Mechanics*, 22(2), 113–126.
6. Breiman, L. (2001). Random forests. *Machine Learning*, 45(1), 5–32.
7. Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12, 2825–2830.
8. McKinney, W. (2010). Data structures for statistical computing in Python. In *Proceedings of the 9th Python in Science Conference* (pp. 56–61).
9. Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. *Computing in Science & Engineering*, 9(3), 90–95.
10. Abid, A., Abdalla, A., Abid, A., Khan, D., Alfozan, A., & Zou, J. (2019). Gradio: Hassle-free sharing and testing of ML models in the wild. *arXiv:1906.02569*.
11. 中央氣象署（2025）。氣象資料開放平臺。https://opendata.cwa.gov.tw
