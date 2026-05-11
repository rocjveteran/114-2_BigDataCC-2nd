#!/usr/bin/env python3
"""
從中央氣象署開放資料平臺取得浮標海象觀測資料，
寫入 sea_observations 表，供後續分析與模擬資料對照。

API 金鑰申請（免費）：https://opendata.cwa.gov.tw/user/api/info
Dataset ID：M-A0064-001（海氣象觀測資料）

未設定 CWA_API_KEY 時，自動切換為季節性模擬海象資料（仍具分析參考價值）。

執行方式：
    docker compose run analysis python fetch_sea_data.py
"""

import os
import random
from datetime import date, datetime, timedelta

import mysql.connector
import requests

# ── 連線設定 ──────────────────────────────────────────────────────────────────
DB = {
    "host":     os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "maritime_duty"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
}

CWA_API_KEY = os.getenv("CWA_API_KEY", "")
CWA_BASE    = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
DATASET_ID  = "M-A0064-001"  # 海氣象觀測資料（浮標站）

# 分析期間
START = date(2025, 11, 1)
END   = date(2026,  4, 30)

# 浮標觀測站（臺灣周邊主要站點）
STATIONS = [
    ("46694", "彭佳嶼"),
    ("46735", "花蓮外海"),
    ("46757", "東沙島"),
    ("46714", "鞍部浮標"),
]

# 波高 → 海況 ENUM 對照（依 Douglas 海況等級）
def wave_to_sea_state(h: float) -> str:
    if h < 0.5:   return "平靜"
    if h < 1.25:  return "輕浪"
    if h < 2.5:   return "中浪"
    return "大浪"


# ── 建立資料表 ────────────────────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sea_observations (
  obs_id       INT AUTO_INCREMENT PRIMARY KEY,
  station_id   VARCHAR(20)    NOT NULL,
  station_name VARCHAR(50)    NOT NULL,
  obs_date     DATE           NOT NULL,
  wave_height  DECIMAL(5, 2)  NULL COMMENT '有效波高 (m)',
  wave_period  DECIMAL(5, 2)  NULL COMMENT '波週期 (s)',
  sea_temp     DECIMAL(5, 2)  NULL COMMENT '海面水溫 (°C)',
  sea_state    ENUM('平靜','輕浪','中浪','大浪') NULL,
  data_source  ENUM('cwa_api','synthetic') NOT NULL DEFAULT 'synthetic',
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_station_date (station_id, obs_date),
  INDEX idx_obs_date (obs_date)
) ENGINE=InnoDB;
"""


# ── CWA API 取得資料 ───────────────────────────────────────────────────────────
def fetch_from_cwa(station_id: str) -> list[dict]:
    """呼叫 CWA 開放資料 API，回傳觀測記錄清單。失敗時回傳空清單。"""
    url = f"{CWA_BASE}/{DATASET_ID}"
    params = {
        "Authorization": CWA_API_KEY,
        "format":        "JSON",
        "StationId":     station_id,
        "limit":         500,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        if body.get("success") != "true":
            return []
        records = body["result"]["records"].get("data", [])
        return records
    except Exception as e:
        print(f"  [API 錯誤] {station_id}: {e}")
        return []


def parse_cwa_records(raw: list[dict], station_id: str, station_name: str) -> list[tuple]:
    """將 CWA API 回傳的原始記錄轉為 DB INSERT tuple。"""
    rows = []
    for r in raw:
        try:
            obs_dt  = datetime.fromisoformat(r.get("DateTime", ""))
            obs_d   = obs_dt.date()
            if not (START <= obs_d <= END):
                continue
            wh = float(r.get("WaveHeight", -99) or -99)
            wp = float(r.get("WavePeriod", -99) or -99)
            st = float(r.get("SeaSurfaceTemperature", -99) or -99)
            if wh < 0:
                continue
            rows.append((
                station_id, station_name, obs_d,
                round(wh, 2),
                round(wp, 2) if wp > 0 else None,
                round(st, 2) if st > 0 else None,
                wave_to_sea_state(wh),
                "cwa_api",
            ))
        except Exception:
            continue
    return rows


# ── 季節性模擬備援 ─────────────────────────────────────────────────────────────
# 臺灣周邊海域冬季東北季風期（11–2月）浪況明顯高於春季（3–4月）
MONTHLY_WAVE_PARAMS = {
    11: (1.4, 0.6), 12: (1.6, 0.7),
     1: (1.5, 0.7),  2: (1.3, 0.6),
     3: (0.9, 0.5),  4: (0.7, 0.4),
}

def generate_synthetic(station_id: str, station_name: str) -> list[tuple]:
    """無 API 金鑰時，依台灣海域季節統計生成模擬觀測資料。"""
    rows = []
    d = START
    while d <= END:
        mean, std = MONTHLY_WAVE_PARAMS.get(d.month, (1.0, 0.5))
        wh = max(0.0, random.gauss(mean, std))
        st = random.uniform(20, 27) if d.month <= 2 else random.uniform(22, 28)
        rows.append((
            station_id, station_name, d,
            round(wh, 2),
            round(random.uniform(4, 10), 1),
            round(st, 2),
            wave_to_sea_state(wh),
            "synthetic",
        ))
        d += timedelta(days=1)
    return rows


# ── 寫入資料庫 ────────────────────────────────────────────────────────────────
INSERT_SQL = """
INSERT IGNORE INTO sea_observations
  (station_id, station_name, obs_date, wave_height, wave_period, sea_temp, sea_state, data_source)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def main():
    random.seed(42)
    conn = mysql.connector.connect(**DB)
    cur  = conn.cursor()

    cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    print("資料表 sea_observations 就緒")

    total_api = 0
    total_syn = 0

    for station_id, station_name in STATIONS:
        rows = []

        if CWA_API_KEY:
            print(f"  → 嘗試 CWA API：{station_name} ({station_id})")
            raw  = fetch_from_cwa(station_id)
            rows = parse_cwa_records(raw, station_id, station_name)
            if rows:
                total_api += len(rows)
                print(f"     取得 {len(rows)} 筆 API 資料")

        if not rows:
            print(f"  → 使用季節性模擬資料：{station_name}")
            rows = generate_synthetic(station_id, station_name)
            total_syn += len(rows)

        cur.executemany(INSERT_SQL, rows)
        conn.commit()

    # ── 統計摘要 ─────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM sea_observations")
    total = cur.fetchone()[0]

    cur.execute("SELECT sea_state, COUNT(*) FROM sea_observations GROUP BY sea_state")
    dist  = cur.fetchall()

    cur.execute("""
        SELECT data_source, COUNT(*)
        FROM sea_observations
        GROUP BY data_source
    """)
    sources = cur.fetchall()

    print(f"\n{'='*48}")
    print(f"  觀測記錄總數：{total} 筆")
    print(f"  資料來源：")
    for src, cnt in sources:
        label = "CWA API（真實）" if src == "cwa_api" else "季節性模擬"
        print(f"    {label}：{cnt} 筆")
    print(f"\n  海況分布：")
    for state, cnt in dist:
        print(f"    {state}：{cnt} 筆（{cnt/total*100:.1f}%）")
    print(f"{'='*48}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
