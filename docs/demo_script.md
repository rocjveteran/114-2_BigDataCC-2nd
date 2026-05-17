# Demo 演練腳本

> 期末口頭報告與 Demo 用 ── 第 18 週

預計時長 **10–12 分鐘**。建議事先實際走過一遍計時，並於正式 Demo 前 30 分鐘執行步驟 0 暖機。

---

## 步驟 0｜事前準備（Demo 前 30 分鐘）

```bash
cd 114-2_BigDataCC-2nd

# 確認 docker/.env 存在且非預設值（含我們新的密碼，已 gitignored）
ls docker/.env

# 啟動三容器
cd docker && docker compose up -d
# 等 60 秒讓 MySQL healthcheck 通過

# 若首次部署：產模擬資料 + 跑分析
docker compose run --rm analysis python generate_mock_data.py
docker compose run --rm analysis python analysis.py
```

- 瀏覽器分頁預開：
  - http://localhost:8080（停在登入頁，bypass login throttle 計數已 reset）
  - http://localhost:7860（停在 Gradio 主畫面）
  - https://github.com/rocjveteran/114-2_BigDataCC-2nd（停在 commit history 頁面）
- 簡報投影同步切到 Slide 1
- 終端機備好 `docker compose logs -f` 觀察用

---

## Demo 流程（總長 10–12 分鐘）

### Part 1｜開場與動機（1 分鐘）

**講者：組長**

> 「各位老師同學好，我們是第 2 組，專題題目是『海事勤務值勤雲端管理系統』。
> 上學期我們做了 PHP 打卡系統，只能在 Windows XAMPP 跑、沒有任何分析能力、UI 也很陽春。
> 這學期我們把它改造成 **三容器 Docker 雲端架構** + **Python 資料分析** + **互動式儀表板與艦上視覺化** + **完整的網頁安全強化**。」

**對應投影片：Slide 1–2**

---

### Part 2｜系統架構與技術選型（1 分鐘）

**講者：組長**

> 「整個系統有三個容器：PHP 8.2 / Apache、MySQL 8、Python 3.11 分析。
> 共用 Docker 內部網路，分析圖表透過 named volume 從 Python 容器傳到 PHP 容器顯示。
> 必要技術全部覆蓋：Pandas、Matplotlib/Seaborn、Docker、Git；選擇性技術用了 MySQL、PHP/Apache、Gradio、Jupyter Notebook。
> 設計風格參考 Anthropic 編輯誌風格 — RAL 7013 灰綠主色 + Inter sans-only 字型。」

**對應投影片：Slide 3–4**

---

### Part 3｜Docker 部署 Demo（1 分鐘）

**講者：組長**

切換到終端機展示：

```bash
docker compose ps
```

> 「事前已啟動，可以看到三個容器都 healthy。
> 從零開始的話，只需要 `docker compose up --build` 一行指令加上首次的資料生成腳本，
> 大約 3 分鐘完成全新部署。」

**對應投影片：Slide 10**

---

### Part 4｜登入與 Dashboard 首頁（1.5 分鐘）

**講者：組長**

切到 http://localhost:8080：

1. **登入** `boss1` 帳號 — 強調登入後直接進入 Dashboard（不再是打卡頁）
2. **Dashboard 介紹**：
   - 左側 **sidebar 分群**（個人 / 艦務 / 管理），boss 角色看得到全部
   - **4 個統計卡**：今日狀態、本週時數、本月累計、待批請假
   - **14 天 sparkline**：純 SVG 生成，無第三方圖表庫
   - **今日艦上配置卡**：在勤人數 + 海域/海象 chip
   - **6 個快速導航 tile**
3. 簡單帶過 sidebar 可切換 mobile 漢堡選單（縮窄瀏覽器示範）

> 「Sidebar 用 CSS `:has()` selector 動態 offset 主內容區，桌機固定欄、行動裝置自動滑出。」

**對應投影片：Slide 5**

---

### Part 5｜打卡與艦上人員視覺化（2 分鐘）

**講者：組長**

點 sidebar「值勤打卡」：

1. **打卡 in / out**：點開始值勤 → 點結束值勤，時間立即記錄
2. **艦上人員配置圖（重點）**：
   - 採 **海巡署安平級 (Anping-class) 巡防艦** 真實側面結構
   - 6 個站位（艦橋 / 瞭望台 / 通訊室 / 前甲板 / 後甲板 / 機艙）
   - 在勤人員以彩色圓點顯示在對應位置，**多人自動 2 列折行**
   - 你的位置用粗框高亮
   - 點頂底波浪會隨**今日海象動態變化**（平靜 1 條、輕浪 2 條、中浪/大浪 3 條，振幅與動畫速度同步）
3. **示範海象切換**：以 admin 身份從表單把今日海象從「輕浪」切到「大浪」，波浪變高變快、chip 顏色變橘紅

> 「整張圖是純 inline SVG 配上 PHP 動態座標生成 — 沒用任何前端框架。
> 結構參照真實巡防艦解剖：穿浪艏、駕駛艙、雷達球、信號旗繩、艉部砲座、識別碼斜條都還原了。」

**對應投影片：Slide 6**

---

### Part 6｜艦務與管理頁面（1.5 分鐘）

**講者：組長**

依序點 sidebar：

1. **我的紀錄** — 個人值勤歷史 + 月份篩選
2. **個人檔案** — avatar、累計時數、海域分布長條（純 CSS bar）
3. **艦上人員（Crew）** — 13 人花名冊依職務位置分群、可搜尋/篩選
4. **航次紀錄（Voyages）** — 30 天彙整：每日海域/海象/在勤人數/總時數
5. **管理區**：
   - 勤務總覽 — 表格快速 開始/結束/清除
   - 帳號管理 — 建立員工 / 切換啟用 / 修改密碼

> 「Voyages 把每天視為一次航次，符合海事業務語意。
> Crew 與 admin_users 的差別：前者展示用、後者管理用。」

**對應投影片：Slide 7**

---

### Part 7｜資料分析儀表板（1.5 分鐘）

**講者：組長**

點「分析儀表板」：

> 「12 張圖直接從 Python 容器產生的圖表 volume 讀檔。
> 涵蓋月度趨勢、海域分布、海域 × 海況交互效應、船艦輪替、海況與時數關係、人員出勤熱力圖、請假趨勢、星期模式等。
> 含 2 項統計檢定（單因子 ANOVA / chi-square）跟 4 項描述性洞察。」

**重點解說兩張圖**：

- **`zone_sea_stacked.png`**：外海大浪比例 20%，遠高於港口的 1%，符合常識
- **`hours_boxplot.png`**：大浪天值勤時數中位數比平靜天低 1.5 小時，驗證海象確實影響勤務時數

**對應投影片：Slide 8**

---

### Part 8｜Gradio 互動介面（1.5 分鐘）

**講者：組長**

切到 http://localhost:7860：

1. **預設條件**：全日期、全海域、全船艦
2. 點「執行分析」── 等約 5 秒，圖表出現
3. **演示篩選**：海域只勾「外海」、船艦選 MAR-001、MAR-002
4. 再點「執行分析」── 圖表變動

> 「篩選條件直接組進 SQL WHERE 子句，不是 Python 端 filter。
> 篩選後的圖會存成 `filtered_*.png`，PHP 儀表板會自動優先讀 filtered，無 fallback 全覽。」

**對應投影片：Slide 9**

---

### Part 9｜網頁安全強化（1 分鐘）

**講者：組長**

切到瀏覽器 DevTools → Application → Cookies：

> 「我們最近做了一輪完整安全審查，發現舊版本有 1 個 HIGH + 4 MEDIUM + 3 LOW 問題。」

逐一展示已修補項目：

1. **CSRF token**：DevTools 移除 `_csrf` hidden input 後送出表單 → 看到 403 friendly page
2. **Session cookie**：HttpOnly + SameSite=Lax + 自動 Secure（HTTPS）
3. **登入節流**：故意打錯 5 次 → 鎖定 15 分鐘
4. **API Key 洩漏防護**：對應 Bilibili 大規模 GitHub API Key 洩漏議題，已用 `git-filter-repo` 改寫歷史 + 加強 .gitignore

> 「完整報告在 `docs/security_audit.md`，git history 已乾淨 — `git log -p` 找不到任何 `.env.txt` 或明碼密碼。」

**對應投影片：Slide 10**

---

### Part 10｜GitHub 管理（30 秒）

**講者：組長**

切到 GitHub Repo：

> 「Commit 用 `[分類]` 前綴管理，可以看到 `[docker]`、`[app]`、`[data]`、`[analysis]`、`[docs]`、`[fix]` 完整開發脈絡。
> 重大變更透過 Pull Request 合併、安全修補逐項分 commit 便於追溯。」

**對應投影片：Slide 11**

---

### Part 11｜結語與未來展望（30 秒）

**講者：組長**

> 「未來延續開發可以接中央氣象署即時海象 API 取代模擬資料、
> 用 Keras 做值勤人力需求預測、整合 AIS 即時船位資料疊到艦上配置圖。
> 以上是我們的 Demo，謝謝大家。」

**對應投影片：Slide 12**

---

## Q&A 預設問題與答案

### Q1：為什麼選 Gradio 不用 Flask？

> Gradio 開發速度極快（幾行程式碼就能做出可用介面），對資料分析類的 demo 非常適合。
> Flask 雖更靈活但開發成本高，本專題的互動需求 Gradio 已足夠。

### Q2：資料是真實的嗎？

> 是模擬資料，但機率模型參考真實海事經驗：外海大浪比例顯著高於港口、
> 大浪天會縮短值勤時數。後續可串接中央氣象署 API 取代部分模擬欄位。

### Q3：為什麼要用三個容器？

> 責任分離：PHP 處理使用者介面、MySQL 持久化、Python 做分析。
> 各容器可獨立擴充或替換，例如未來 PHP 換成 Next.js 不影響其他容器。

### Q4：船艦圖為何特別畫安平級？

> 「海事勤務」對應到台灣場景就是海巡署，安平級是現役主力 600 噸雙體巡防艦。
> 真實解剖學畫出來有專業感、辨識度高。整張圖純 SVG 約 50 行 PHP/SVG。

### Q5：MySQL 密碼怎麼處理？怎麼處理 GitHub 洩漏？

> 全部透過環境變數注入。`.env` 已加入 `.gitignore`，`db.php` 用 `getenv()` 讀取。
> 此外發現舊版本曾不小心 commit `.env.txt`，已用 `git-filter-repo` 改寫歷史並 force-push 清除。

### Q6：CSRF 怎麼實作？

> 自製輕量版：`csrf.php` 提供 `csrf_token / csrf_input / csrf_require` 三個函式。
> session 內存 token、每個 POST 表單帶 hidden input、handler 入口校驗、不符 403。
> 不引入任何第三方套件。

### Q7：為什麼分析圖表是 PNG 不是互動 HTML？

> PNG 的好處是 PHP 端不需要 JavaScript runtime 就能嵌入，
> 也方便存檔、加進報告。如果要互動可改用 Plotly + iframe，
> 但會增加 PHP 端的複雜度，我們選擇了較簡單的方案。

### Q8：Docker compose 啟動順序怎麼處理？

> `depends_on` 配合 `healthcheck`：web 和 analysis 容器會等 MySQL 健康後才啟動，
> 避免連線失敗。

### Q9：UI 為何選 RAL 7013 灰綠？

> 海事氛圍（軍規／北約色系常見）、可讀性高、配上 Claude 橘做行動色形成對比。
> 整套色票在 `style.css` 開頭一處定義，全站變數化。

---

## 應變預案

| 情況 | 預案 |
|------|------|
| 投影機接不上 | 用筆電直接展示，請後排同學前移 |
| Docker 啟動失敗 | 切到備用機（事前準備）；或直接展示 GitHub repo + 投影片講解 |
| Gradio 卡頓 | 切回 PHP 儀表板（已預先產生圖表），展示靜態結果 |
| 網路斷線 | 全部使用 localhost，不需網路；GitHub 部分用截圖代替 |
| 登入節流卡到自己 | 切換到 admin1 帳號（不同 session 不會被鎖） |
| 超時 | 跳過 Part 9 安全段落只做 30 秒口述、Q&A 只保留 Q1–Q4 |

---

## 分工

| 組員 | Demo 角色 |
|------|----------|
| 黃宇平（組長） | 主講、操作系統 |
| 傅瀚鋌 | 投影片翻頁、計時提醒 |
| 曾紹喆 | Q&A 補充（分析洞察） |
| 劉家样 | 備用筆電操作員 |
| 李翊丞 | 開場介紹、結語 |
| 林秉賢 | 會後資料整理 |
