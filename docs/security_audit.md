# 海事勤務值勤管理系統 · 安全審查報告

審查日期：2026-05-16
審查者：Claude Opus 4.7
範圍：`src/app/*.php`、`docker/`、git 歷史、根目錄敏感檔

---

## 觸發來源：Bilibili《GitHub 上正在發生大規模 API Key 洩漏事件》

影片要點：開發者把 API Key、DB 連線、認證 token 等敏感字串誤 commit 到 git，再 push 上公開 GitHub，攻擊者可大規模掃描 → 取得有效金鑰 → 直接濫用 API quota / 入侵後端。

**本專案對照**：直接命中 — `.env.txt` 含明碼資料庫密碼曾 push 到 `origin/main`（見 H-1）。其餘第三方 API 金鑰（AWS、OpenAI、GitHub token、Google API）皆未洩漏。

---

## 嚴重度總覽

| 嚴重度 | 項目 | 狀態 |
|--------|------|------|
| **HIGH** | H-1：DB 密碼 commit 至 git 歷史並推上公開 origin | 待你決定是否輪換、是否改寫歷史 |
| **MEDIUM** | M-1：全站 POST 表單缺 CSRF token | 本次自動修補 |
| **MEDIUM** | M-2：登入無暴力破解節流 | 本次自動修補 |
| **MEDIUM** | M-3：session cookie 屬性未硬化 | 本次自動修補 |
| **MEDIUM** | M-4：`schema.sql` 註解暴露預設明碼密碼 | 本次自動修補（改為指向 docs） |
| **LOW** | L-1：`logout.php` 走 GET，可被圖片注入觸發強制登出 | 本次自動修補 |
| **LOW** | L-2：未顯式關閉 `display_errors` | 本次自動修補 |
| **LOW** | L-3：`admin_export.php` Content-Disposition 未過濾 | 本次自動修補 |
| OK | XSS / SQL Injection / Authorization / bcrypt | 無發現 |

---

## H-1 · DB 密碼 commit 至 git 歷史 ⚠️ HIGH

### 發現
- 檔案 `.env.txt` 含明碼密碼於 commit `4a206ac3bb681e72df16c0d7e7594c95fc6bfd35`（"update", 2026-05-11）被加入版本控制
- 後於 commit `f64bb708401523ce110086c7db97c616b881a9ce`（2026-05-12）被刪除
- **commit `4a206ac` 仍存在於 `origin/main`**，任何人 `git clone` 後 `git log -p` 可看到密碼
- 洩漏內容：
  - `DB_ROOT_PASS=[REDACTED-ROOT-PWD]`
  - `DB_PASS=[REDACTED-USER-PWD]`
- **目前 `docker/.env` 仍使用同一組密碼**，所以執行中的 DB 真實密碼就是這組已公開的字串

### 影響
- 若 MySQL port 曾暴露到 public network → 任何掃描者可直接登入
- 即使 Docker 內部網路隔離，密碼一旦泄漏即視為失守，應該輪換
- 攻擊者可從 GitHub 公開歷史複製 `.env.txt` 後重現本地環境，但不能直接攻擊未暴露之 DB

### 補救選項（皆需你同意，不自動執行）

| 選項 | 動作 | 副作用 |
|------|------|--------|
| A | 輪換密碼：改寫 `docker/.env`、`docker exec mysql` 跑 `ALTER USER ... IDENTIFIED BY ...`、重啟 web 容器 | 不破壞性，最小代價，仍留下歷史污點 |
| B | git 歷史改寫：`git filter-repo --invert-paths --path .env.txt` 後 `git push --force` | 破壞性，已 push 給 GitHub 也仍可能被快照；協作者需重新 clone |
| C | 同時 A + B + 撤銷舊密碼 | 最完整 |
| D | 教育用途接受風險，只更新 `.gitignore` 並加註解 | 最弱 |

**建議**：A（輪換）必做。B（改寫歷史）視專案是否要對外公開的程度決定。本次自動執行**只能做到 A 的「先改檔不執行 ALTER」**，等你回來確認後 `docker exec` 跑 ALTER 一行就完成。

---

## M-1 · POST 表單缺 CSRF token ⚠️ MEDIUM

### 發現
9 個 PHP 接受 POST，全部沒有 CSRF token：
`login.php`, `punch.php`, `leave.php`, `admin_create_user.php`, `admin_edit.php`, `admin_user_edit.php`, `admin_users.php`, `admin_leave.php`, `admin_status.php`

### 影響
登入中的使用者點到攻擊者準備的網頁 → 該網頁自動 POST 至本系統 → cookies 跟著送 → 以使用者身分執行操作（變更密碼、刪除帳號、批准請假、結束他人值勤等）

### 修補（本次自動執行）
- 新增 `csrf.php`：`csrf_token()` / `csrf_verify()` / `csrf_input()` 三個函式
- `ui.php` 載入 csrf
- 9 個 POST 表單加入 `<input type="hidden" name="_csrf" value="...">`
- 9 個 POST 處理進入點呼叫 `csrf_verify()`，不符即 403

---

## M-2 · 登入無節流 ⚠️ MEDIUM

### 發現
`login.php` 無任何嘗試次數限制，攻擊者可無限重試。

### 修補（本次自動執行）
- 在 `login.php` 加入 session-based 節流：同一 session 5 次連續失敗即鎖定 15 分鐘
- 失敗計數與最後失敗時間存於 `$_SESSION['login_fail_*']`
- 鎖定期間 UI 提示「請稍候 N 分鐘」
- 注意：session-based 對攻擊者只要換 cookie 即繞過，建議後續加 DB 層 IP-based。本次先做 baseline

---

## M-3 · session cookie 未硬化 ⚠️ MEDIUM

### 發現
無任何 `session_set_cookie_params()` 設定，依 PHP/Apache 預設：
- HttpOnly：未設（可能被 JS 讀）
- SameSite：未設（容易被跨站 form POST 用上）
- Secure：未設（即使裝 HTTPS 也會以明文走）
- `session.use_strict_mode`：未開（容易 session fixation）

### 修補（本次自動執行）
- 在 `ui.php` 的 session_start 前加 `session_set_cookie_params([httponly=true, samesite=Lax, secure=auto-detect HTTPS])` + `ini_set('session.use_strict_mode', '1')`

---

## M-4 · schema.sql 暴露預設密碼 ⚠️ MEDIUM

### 發現
```sql
('boss1', '$2y$...', ...); -- password: boss1234
('admin1', '$2y$...', ...); -- password: admin1234
('em1', '$2y$...', ...); -- password: em1234
```
雖然存的是 bcrypt hash，但註解直接公開明碼。

### 修補（本次自動執行）
- 移除註解中的明碼，改成指向 `docs/demo_credentials.md`（新增）
- 新建 `docs/demo_credentials.md` 並 `.gitignore` 之，僅本地有

---

## L-1 · logout.php 經 GET 觸發 ⚠️ LOW

### 發現
`logout.php` 直接 `session_destroy()`，方法不限 GET/POST。攻擊者可在留言區放 `<img src="/logout.php">` 強制其他登入者登出（DoS-like，不嚴重但煩人）。

### 修補（本次自動執行）
- `logout.php` 改為僅接受 POST + CSRF token 驗證
- sidebar 的「登出」連結改為 `<form method="post">`

---

## L-2 · PHP error 顯示未明確關閉 ⚠️ LOW

### 發現
無 `ini_set('display_errors', '0')`，依容器配置可能在頁面噴出檔案路徑、SQL、堆疊。

### 修補（本次自動執行）
- `db.php` 開頭加入：若 `getenv('APP_ENV') !== 'dev'`，則關閉 display_errors、開 log_errors

---

## L-3 · admin_export.php Content-Disposition ⚠️ LOW

### 發現
```php
header('Content-Disposition: attachment; filename="duty_'.$d.'.csv"');
```
`$d` 來自 `$_GET['d']` 未驗證；可注入 CRLF 之類字符到 header（HTTP response splitting）。

### 修補（本次自動執行）
- 在使用前以 `preg_match('/^\d{4}-\d{2}-\d{2}$/', $d)` 驗證；不符即用 `date('Y-m-d')`

---

## 未發現的攻擊面（已掃描，無問題）

| 類別 | 狀態 |
|------|------|
| SQL Injection | 全站使用 PDO prepared statements |
| XSS | 所有輸出皆經 `h()` (htmlspecialchars) |
| 第三方 API Key 洩漏（AWS、OpenAI、GitHub token、Google API、Slack） | 未發現 |
| Authorization (admin endpoint 權限) | `can_manage_user()` 覆蓋完整 |
| Password hashing | bcrypt (`PASSWORD_DEFAULT`) ✓ |
| Session regeneration on login | 已做 ✓ |
| Path traversal | `admin_dashboard.php` 的 `file_get_contents` 使用硬編碼路徑 |
| File upload | 系統無檔案上傳功能 |

---

## 修補後須請你執行的人工動作

1. **輪換 DB 密碼**（H-1）：
   ```bash
   # 1. 修改 docker/.env 任一新值（非 [REDACTED-ROOT-PWD]）
   # 2. 在 DB 內 ALTER:
   docker exec docker-db-1 mysql -uroot -p'[REDACTED-ROOT-PWD]' -e \
     "ALTER USER 'root'@'%' IDENTIFIED BY '新root密碼'; \
      ALTER USER 'maritime_user'@'%' IDENTIFIED BY '新user密碼'; \
      FLUSH PRIVILEGES;"
   # 3. 重啟 web/analysis 容器讓它讀新 .env：
   docker compose restart web analysis
   ```

2. **（選擇性）改寫 git 歷史抹去 `.env.txt`**：
   ```bash
   # 此操作會 force-push，需通知所有協作者重新 clone
   pip install git-filter-repo
   git filter-repo --invert-paths --path .env.txt
   git push --force origin main
   ```

3. **更新預設帳號密碼**（M-4）：若部署上線，請在 schema 載入後立即 `UPDATE users SET password_hash=... WHERE username='boss1'`。

---

## 自動修補的 commits 列表

| Commit | 涵蓋項目 |
|--------|----------|
| `0bd4500` | M-1 CSRF token 系統 + 9 個 POST 端點 + sidebar logout |
| `0bd4500` | M-2 登入失敗節流（5 次/15 分鐘） |
| `0bd4500` | M-3 session 硬化（HttpOnly / SameSite / use_strict_mode） |
| `0bd4500` | L-1 logout 改為 POST + CSRF + 303 redirect |
| `a6511ad` | M-4 schema 註解明碼移除 + demo_credentials.md (gitignored) |
| `a6511ad` | L-2 db.php APP_ENV-guarded error reporting |
| `a6511ad` | L-3 admin_export.php 日期格式嚴格驗證 |

## H-1 狀態：**未自動修補**（需你同意）

git 歷史的 `.env.txt` 仍存在於 `origin/main`，現行 `docker/.env` 仍使用同組已洩漏密碼。
看本檔上方「補救選項」決定如何處理；建議至少執行選項 A（密碼輪換）。
