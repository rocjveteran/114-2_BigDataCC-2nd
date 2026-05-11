#!/usr/bin/env python3
"""
產生六個月模擬海事值勤資料（約 800-1200 筆）並寫入 MySQL。

使用方式（在 docker 環境中）：
    docker compose run analysis python generate_mock_data.py

使用方式（本機直接執行）：
    DB_HOST=localhost DB_NAME=maritime_duty DB_USER=root DB_PASS= python generate_mock_data.py
"""

import os
import random
from datetime import date, datetime, timedelta

import bcrypt
import mysql.connector

# ── 連線設定 ──────────────────────────────────────────────────────────────────
DB = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "maritime_duty"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
}

# ── 時間範圍（六個月）────────────────────────────────────────────────────────
START = date(2025, 11, 1)
END   = date(2026, 4, 30)

# ── 模擬人員（schema.sql 已建 boss1/admin1/em1，此處補充） ────────────────────
# 密碼統一為 maritime2025，可由管理員後台修改
_DEFAULT_PW = b"maritime2025"

EXTRA_USERS = [
    ("chen_wei",   "陳偉",   "employee"),
    ("lin_jia",    "林佳",   "employee"),
    ("wang_ming",  "王明",   "employee"),
    ("zhang_hong", "張宏",   "employee"),
    ("liu_yan",    "劉燕",   "employee"),
    ("huang_jun",  "黃峻",   "employee"),
    ("zhao_lei",   "趙磊",   "admin"),
    ("sun_fang",   "孫芳",   "employee"),
    ("wu_chao",    "吳超",   "employee"),
    ("zheng_yu",   "鄭宇",   "employee"),
]

# ── 船艦清單 ──────────────────────────────────────────────────────────────────
VESSELS = [
    "MAR-001", "MAR-002", "MAR-003", "MAR-004",
    "MAR-005", "MAR-006", "MAR-007", "MAR-008",
]

# ── 值勤海域機率 ──────────────────────────────────────────────────────────────
ZONE_WEIGHTS = {"港口": 0.35, "近海": 0.40, "外海": 0.25}

# 各海域的海況機率（外海大浪機率較高）
SEA_WEIGHTS = {
    "港口": {"平靜": 0.70, "輕浪": 0.25, "中浪": 0.04, "大浪": 0.01},
    "近海": {"平靜": 0.40, "輕浪": 0.35, "中浪": 0.20, "大浪": 0.05},
    "外海": {"平靜": 0.15, "輕浪": 0.30, "中浪": 0.35, "大浪": 0.20},
}

# 大浪時提前收班（分鐘）
EARLY_CHECKOUT = {"平靜": 0, "輕浪": -20, "中浪": -50, "大浪": -100}


# ── 輔助函式 ──────────────────────────────────────────────────────────────────
def pick_zone():
    keys, weights = zip(*ZONE_WEIGHTS.items())
    return random.choices(keys, weights=weights)[0]


def pick_sea(zone):
    d = SEA_WEIGHTS[zone]
    keys, weights = zip(*d.items())
    return random.choices(keys, weights=weights)[0]


def make_checkin(d: date) -> datetime:
    """07:00 – 09:00 之間隨機"""
    return datetime(d.year, d.month, d.day, 7, 0) + timedelta(minutes=random.randint(0, 120))


def make_checkout(checkin: datetime, sea: str) -> datetime:
    """17:00 基準，依海況提前，再加 ±15 min 抖動"""
    base = checkin.replace(hour=17, minute=0, second=0, microsecond=0)
    delta = EARLY_CHECKOUT[sea] + random.randint(-15, 60)
    return base + timedelta(minutes=delta)


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def hash_pw(pw: bytes) -> str:
    # $2b$ prefix，PHP password_verify() 對 $2b$ 與 $2y$ 皆相容
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=10)).decode()


# ── 主程式 ────────────────────────────────────────────────────────────────────
def main():
    conn = mysql.connector.connect(**DB)
    cur  = conn.cursor()

    # 1. 插入額外人員
    pw_hash = hash_pw(_DEFAULT_PW)
    for uname, fname, role in EXTRA_USERS:
        cur.execute(
            "INSERT IGNORE INTO users (username, password_hash, full_name, role) VALUES (%s,%s,%s,%s)",
            (uname, pw_hash, fname, role),
        )
    conn.commit()
    print(f"  人員建立完畢（密碼：maritime2025）")

    # 2. 取得所有可值班人員（role != boss）
    cur.execute("SELECT user_id FROM users WHERE role IN ('admin','employee') AND is_active=1")
    user_ids = [r[0] for r in cur.fetchall()]

    # 每人指定主責船艦（8 艘輪替）
    vessel_map = {uid: VESSELS[i % len(VESSELS)] for i, uid in enumerate(user_ids)}

    all_days = list(daterange(START, END))

    # 3. 產生值勤記錄
    att_rows = []
    for uid in user_ids:
        for d in all_days:
            if d.weekday() == 6:          # 週日固定休
                continue
            if random.random() > 0.76:    # 約 76% 出勤率
                continue

            zone    = pick_zone()
            sea     = pick_sea(zone)
            ci      = make_checkin(d)
            co      = make_checkout(ci, sea)
            vessel  = vessel_map[uid]

            att_rows.append((uid, d, ci, co, "done", zone, sea, vessel))

    # 控制在 800–1200 筆之間
    if len(att_rows) > 1200:
        att_rows = random.sample(att_rows, 1200)

    cur.executemany(
        """INSERT IGNORE INTO attendance
               (user_id, work_date, check_in, check_out, status, duty_zone, sea_state, vessel_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        att_rows,
    )
    conn.commit()

    # 4. 產生請假記錄
    leave_types    = ["personal", "sick", "other"]
    leave_statuses = ["approved", "approved", "approved", "rejected", "pending"]  # 加權
    leave_rows     = []

    for uid in user_ids:
        for _ in range(random.randint(3, 8)):
            offset  = random.randint(0, (END - START).days - 3)
            s_date  = START + timedelta(days=offset)
            e_date  = min(s_date + timedelta(days=random.randint(0, 2)), END)
            ltype   = random.choice(leave_types)
            status  = random.choice(leave_statuses)
            dec_by  = None
            dec_at  = None
            if status in ("approved", "rejected"):
                dec_by = 1  # boss1
                dec_at = datetime.combine(s_date, datetime.min.time()).replace(hour=9)

            leave_rows.append((uid, s_date, e_date, ltype, status, dec_by, dec_at))

    cur.executemany(
        """INSERT INTO leaves (user_id, date_from, date_to, leave_type, status, decided_by, decided_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        leave_rows,
    )
    conn.commit()

    # 5. 統計摘要
    cur.execute("SELECT COUNT(*) FROM attendance")
    att_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM leaves")
    leave_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users")
    user_total = cur.fetchone()[0]

    cur.execute("SELECT duty_zone, COUNT(*) FROM attendance GROUP BY duty_zone")
    zone_dist = cur.fetchall()

    cur.execute("SELECT sea_state, COUNT(*) FROM attendance GROUP BY sea_state")
    sea_dist = cur.fetchall()

    print(f"\n{'='*40}")
    print(f"  人員總數：{user_total} 人")
    print(f"  值勤記錄：{att_total} 筆")
    print(f"  請假記錄：{leave_total} 筆")
    print(f"\n  海域分布：")
    for zone, cnt in zone_dist:
        print(f"    {zone}：{cnt} 筆")
    print(f"\n  海況分布：")
    for sea, cnt in sea_dist:
        print(f"    {sea}：{cnt} 筆")
    print(f"{'='*40}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    random.seed(42)
    main()
