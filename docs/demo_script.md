# Demo 演練腳本

> 期末口頭報告與 Demo 用 ── 第 18 週

預計時長 **8–10 分鐘**。建議事先實際走過一遍計時，並於正式 Demo 前 30 分鐘執行步驟 0 暖機。

---

## 步驟 0｜事前準備（Demo 前 30 分鐘）

```bash
cd 114-2_BigDataCC-2nd
cp .env.example docker/.env              # 先確認 docker/.env 存在
docker compose -f docker/docker-compose.yml down -v   # 清空舊資料
docker compose -f docker/docker-compose.yml up --build -d
# 等待約 60 秒讓 MySQL healthcheck 通過

docker compose -f docker/docker-compose.yml run --rm analysis python generate_mock_data.py
docker compose -f docker/docker-compose.yml run --rm analysis python analysis.py
```

- 瀏覽器分頁預開：
  - http://localhost:8080（停在登入頁）
  - http://localhost:7860（停在 Gradio 主畫面）
- 終端機分頁預備：可隨時 `docker compose logs` 觀察
- 簡報投影同步切到 Slide 1

---

## Demo 流程（總長 8–10 分鐘）

### Part 1｜開場與動機（1 分鐘）

**講者：組長**

> 「各位老師同學好，我們是第 2 組，專題題目是『海事勤務值勤雲端管理系統』。
> 上學期我們做了 PHP 打卡系統，但只能在 Windows XAMPP 跑，也沒有任何分析能力。
> 這學期我們把它改造成三容器 Docker 雲端架構，加上 Python 資料分析跟 Gradio 互動介面。」

**對應投影片：Slide 1–2**

---

### Part 2｜系統架構與技術選型（1 分鐘）

**講者：組長**

> 「整個系統有三個容器：PHP/Apache、MySQL、Python 分析。
> 共用 Docker 內部網路，分析圖表透過 named volume 從 Python 容器傳到 PHP 容器顯示。
> 必要技術全部覆蓋：Pandas、Matplotlib/Seaborn、Docker、Git；選擇性技術用了 MySQL、PHP/Apache、Gradio。」

**對應投影片：Slide 3–4**

---

### Part 3｜Docker 部署 Demo（1 分鐘）

**講者：組長**

切換到終端機，展示一行指令啟動：

```bash
docker compose -f docker/docker-compose.yml ps
```

> 「事前已啟動，可以看到三個容器都健康。
> 從零開始的話，只需要 `docker compose up --build` 這一行指令，
> 加上首次的資料生成腳本，大約 3 分鐘就能完成全新部署。」

**對應投影片：Slide 10**

---

### Part 4｜PHP 系統功能（2 分鐘）

**講者：組長**

切到 http://localhost:8080 ：

1. **登入** `boss1` 帳號（強調權限分層）
2. **打卡頁** ── 點擊上勤、下勤，顯示當日記錄
3. **我的值勤** ── 個人歷史
4. **請假申請** ── 填一筆 demo 假
5. **管理介面** ──
   - 值勤總覽（顯示模擬資料量）
   - 請假審核（核准剛才那筆）
   - 帳號管理（看到 10 位模擬人員）

> 「`db.php` 從寫死的 root + 空密碼改成讀取環境變數，
> schema 也擴充了 duty_zone、sea_state、vessel_id 三個海事欄位。」

**對應投影片：Slide 9**

---

### Part 5｜資料分析儀表板（1.5 分鐘）

**講者：組長**

PHP 介面點擊「分析儀表板」：

> 「這頁直接從 Python 容器產生的圖表 volume 讀檔，所以更新時間是分析最後一次執行的時刻。
> 七張圖涵蓋月度趨勢、海域分布、海域 × 海況、船艦輪替、海況與時數關係、人員出勤熱力圖、請假趨勢。」

**重點解說兩張圖**：

- **`zone_sea_stacked.png`**：「外海大浪比例 20%，遠高於港口的 1%，符合常識。」
- **`hours_boxplot.png`**：「大浪天值勤時數中位數比平靜天低 1.5 小時，驗證海象確實影響勤務時數。」

**對應投影片：Slide 7**

---

### Part 6｜Gradio 互動介面（2 分鐘）

**講者：組長**

切到 http://localhost:7860 ：

1. **預設條件**：全日期、全海域、全船艦
2. 點「執行分析」── 等約 5 秒，七張圖出現
3. **演示篩選**：海域只勾「外海」，船艦選 MAR-001、MAR-002
4. 再點「執行分析」── 圖表變動

> 「篩選條件直接組進 SQL WHERE 子句，不是 Python 端 filter，
> 即使資料量上萬筆也能快速回應。
> 篩選後的圖會存成 `filtered_*.png`，不會覆蓋全覽圖表。」

**對應投影片：Slide 8**

---

### Part 7｜GitHub 管理（30 秒）

**講者：組長**

切到 GitHub Repo：

> 「Commit 用 [分類] 前綴管理，可以看到從 docker、app、data、analysis 到 docs 的完整開發脈絡。
> 第 14 週開始的所有變更都透過 Pull Request 合併到 main。」

**對應投影片：Slide 11**

---

### Part 8｜結語與未來展望（30 秒）

**講者：組長**

> 「未來如果延續開發，可以接中央氣象署即時海象 API 取代模擬資料、
> 用 Keras 做值勤人力需求預測、或整合 AIS 船位資料。
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

### Q4：MySQL 密碼怎麼處理？

> 全部透過環境變數注入。`.env` 已加入 `.gitignore`，
> `db.php` 用 `getenv()` 讀取，原本寫死的 root + 空密碼問題已解決。

### Q5：為什麼分析圖表是 PNG 不是互動 HTML？

> PNG 的好處是 PHP 端不需要 JavaScript runtime 就能嵌入，
> 也方便存檔、加進報告。如果要互動可改用 Plotly + iframe，
> 但會增加 PHP 端的複雜度，我們選擇了較簡單的方案。

### Q6：為什麼模擬資料的密碼都一樣？

> Demo 用途，10 位模擬人員都是 `maritime2025`。
> 真實部署時 admin 可以強制改密碼。

### Q7：Docker compose 啟動順序怎麼處理？

> `depends_on` 配合 `healthcheck`：web 和 analysis 容器會等 MySQL 健康後才啟動，
> 避免連線失敗。

---

## 應變預案

| 情況 | 預案 |
|------|------|
| 投影機接不上 | 用筆電直接展示，請後排同學前移 |
| Docker 啟動失敗 | 切到備用機（事前準備）；或直接展示 GitHub repo + 投影片講解 |
| Gradio 卡頓 | 切回 PHP 儀表板（已預先產生圖表），展示靜態結果 |
| 網路斷線 | 全部使用 localhost，不需網路；GitHub 部分用截圖代替 |
| 超時 | 跳過 Q&A 預設第 5–7 題，只保留 Q1–Q4 |

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
