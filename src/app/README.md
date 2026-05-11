# 簡易 PHP 值勤出勤管理系統（XAMPP 版 / 最小可行 MVP）

## 功能（最少動作、最少出錯）
- 員工登入（session）
- 一鍵打卡：自動判斷「上班 / 下班」
- 查詢自己的打卡紀錄（日期區間）

## 環境需求
- Windows + XAMPP（Apache, MySQL）
- phpMyAdmin

## 安裝步驟（最快）
1. 將整個資料夾 `punch_attendance_xampp` 複製到：
   `C:\xampp\htdocs\punch\`
2. 啟動 XAMPP：Apache + MySQL
3. phpMyAdmin 匯入 `schema.sql` 建立資料庫與資料表
4. 開瀏覽器執行一次（建立測試帳號 emp1/1234）：
   `http://localhost/myproject/init_admin.php`
   執行完請刪除 `init_admin.php`
5. 開啟登入頁：
   `http://localhost/myproject/login.php`

## 預設資料庫連線
請看 `db.php`：
- host: localhost
- db: punch_db
- user: root
- pass: (空白)

## 資料表設計重點（避免重複打卡）
- `attendance` 設定 UNIQUE(user_id, work_date)：
  一天只能有一筆主紀錄，第二次打卡只更新 check_out。

## 文件
- `docs/`：包含期末報告 docx 與 ER/系統圖（如有）


## 預設管理者帳號（已內建在 schema.sql）
- username: test1
- password: 0000

## 管理者新增帳號
1. 先用管理者登入：`login.php`
2. 開：`admin_create_user.php`
3. 輸入 username / full_name / password，即可建立員工帳號


## 管理者查看/修改每日狀態
- 查看每日狀態（預設今天）：`http://localhost/myproject/admin_status.php`
- 編輯某人某日：在狀態表點「編輯」即可


## 匯出 CSV
- 管理：每日狀態頁提供匯出 CSV：`admin_export.php?d=YYYY-MM-DD`


## 介面
- 共用樣式：style.css
- 共用導覽/標籤：ui.php


## 請假系統
- 員工：`leave.php` 送出請假申請（待審核）
- 管理者：`admin_leave.php` 核准/拒絕
- 值勤總覽：若當日為「已核准請假」，狀態顯示「請假」
- 匯出日報表(CSV)：會包含 leave 欄位


## 介面加強
- 值勤總覽提供快速操作：開始(現在)/結束(現在)/清除
- 請假頁可取消「待審核」申請


## 管理者帳號管理
- 列表/搜尋/啟用停用：`admin_users.php`
- 修改帳號/重設密碼：`admin_user_edit.php?uid=...`


## 系統名稱
- 介面顯示名稱：海勤值勤管理系統



## 權限角色
- boss：可管理 boss/admin/employee（包含自己）
- admin：只能管理 employee
- employee：只能查看（不可操作）



## 預設帳號
- boss1 / 0001
- admin1 / 0002
- em1 / 0003


## 進入入口
- 直接開 `http://localhost/myproject/` 會先清除登入狀態並導向登入頁（方便展示）。
