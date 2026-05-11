#!/usr/bin/env python3
"""
資料清洗、Pandas 統計分析、Matplotlib/Seaborn 圖表生成。
可作為獨立腳本執行，也可由 app.py（Gradio）呼叫 generate_charts()。

執行方式：
    docker compose run analysis python analysis.py
"""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import pandas as pd
import mysql.connector

# ── 連線設定 ──────────────────────────────────────────────────────────────────
_DB = {
    "host":        os.getenv("DB_HOST", "localhost"),
    "database":    os.getenv("DB_NAME", "maritime_duty"),
    "user":        os.getenv("DB_USER", "root"),
    "password":    os.getenv("DB_PASS", ""),
    "charset":     "utf8mb4",
    "use_unicode": True,
}

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))

# ── 中文字型 ──────────────────────────────────────────────────────────────────

import glob as _glob

def _find_cjk_font():
    patterns = [
        "/usr/share/fonts/**/*CJK*.ttc",
        "/usr/share/fonts/**/*CJK*.ttf",
        "/usr/share/fonts/**/*Noto*CJK*.otf",
        "/usr/share/fonts/**/*noto*cjk*.ttf",
    ]
    for p in patterns:
        files = _glob.glob(p, recursive=True)
        if files:
            return files[0]
    return None

_cjk_file = _find_cjk_font()
if _cjk_file:
    fm.fontManager.addfont(_cjk_file)
    _cjk_prop = fm.FontProperties(fname=_cjk_file)
    _cjk_name = _cjk_prop.get_name()
else:
    _cjk = [f.name for f in fm.fontManager.ttflist if "Noto" in f.name and "CJK" in f.name]
    _cjk_name = _cjk[0] if _cjk else "DejaVu Sans"

BLUE_PAL = ["#0D47A1", "#1565C0", "#1976D2", "#1E88E5", "#42A5F5", "#90CAF9"]
# set_theme 會重置 rcParams，字型設定必須在它之後
sns.set_theme(style="whitegrid", palette=BLUE_PAL)
plt.rcParams["font.family"] = [_cjk_name, "DejaVu Sans"]
plt.rcParams["font.sans-serif"] = [_cjk_name, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# ── 公開 API（供 app.py 呼叫）────────────────────────────────────────────────
def get_connection():
    return mysql.connector.connect(**_DB)


def get_filter_options(conn) -> dict:
    """回傳 Gradio 下拉選單用的選項清單。"""
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT vessel_id FROM attendance WHERE vessel_id IS NOT NULL ORDER BY vessel_id")
    vessels = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT duty_zone FROM attendance WHERE duty_zone IS NOT NULL")
    zones = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT MIN(work_date), MAX(work_date) FROM attendance")
    date_min, date_max = cur.fetchone()
    cur.close()
    return {"vessels": vessels, "zones": zones, "date_min": date_min, "date_max": date_max}


def generate_charts(
    output_dir: Path | None = None,
    date_from=None,
    date_to=None,
    zones: list | None = None,
    vessels: list | None = None,
) -> list[str]:
    """
    產生所有圖表，回傳 PNG 檔路徑清單（依固定順序）。
    若提供篩選參數則只分析該子集，同時加上 filtered_ 前綴另存，
    不覆蓋全覽圖表。
    """
    out = Path(output_dir) if output_dir else OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    prefix = "filtered_" if any([date_from, date_to, zones, vessels]) else ""

    conn = get_connection()
    att, leaves = _load_data(conn, date_from, date_to)
    conn.close()

    att, leaves = _clean(att, leaves)

    # 篩選在 _clean 之後執行，確保 duty_zone/vessel_id 已從 bytes 轉為 str
    if zones:
        att = att[att["duty_zone"].isin(zones)]
    if vessels:
        att = att[att["vessel_id"].isin(vessels)]

    paths = []
    for fn, chart_fn in [
        (f"{prefix}monthly_trend.png",   lambda: _chart_monthly_trend(att)),
        (f"{prefix}zone_bar.png",         lambda: _chart_zone_bar(att)),
        (f"{prefix}zone_sea_stacked.png", lambda: _chart_zone_sea_stacked(att)),
        (f"{prefix}vessel_count.png",     lambda: _chart_vessel_count(att)),
        (f"{prefix}hours_boxplot.png",    lambda: _chart_hours_boxplot(att)),
        (f"{prefix}person_heatmap.png",   lambda: _chart_person_heatmap(att)),
        (f"{prefix}leave_trend.png",      lambda: _chart_leave_trend(leaves)),
    ]:
        fig = chart_fn()
        path = out / fn
        fig.savefig(path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"  ✔ {fn}")
        paths.append(str(path))

    return paths


# ── 資料載入 ──────────────────────────────────────────────────────────────────
def _load_data(conn, date_from, date_to):
    where = ["a.status = 'done'"]
    params: list = []

    if date_from:
        where.append("a.work_date >= %s"); params.append(date_from)
    if date_to:
        where.append("a.work_date <= %s"); params.append(date_to)

    sql_att = f"""
        SELECT a.att_id, a.user_id, u.full_name, u.role,
               a.work_date, a.check_in, a.check_out,
               a.duty_zone, a.sea_state, a.vessel_id
        FROM   attendance a
        JOIN   users u ON a.user_id = u.user_id
        WHERE  {' AND '.join(where)}
    """
    att = pd.read_sql(sql_att, conn, params=params or None,
                      parse_dates=["work_date", "check_in", "check_out"])

    leaves = pd.read_sql(
        """SELECT l.leave_id, l.user_id, u.full_name,
                  l.date_from, l.date_to, l.leave_type, l.status
           FROM   leaves l JOIN users u ON l.user_id = u.user_id""",
        conn, parse_dates=["date_from", "date_to"],
    )
    return att, leaves


# ── 資料清洗 ──────────────────────────────────────────────────────────────────
def _clean(att: pd.DataFrame, leaves: pd.DataFrame):
    before = len(att)
    att = att.dropna(subset=["check_in", "check_out", "duty_zone", "sea_state", "vessel_id"]).copy()
    for col in ["duty_zone", "sea_state", "vessel_id"]:
        att[col] = att[col].apply(lambda x: x.decode("utf-8") if isinstance(x, bytes) else str(x))
    att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600
    att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]
    if before - len(att):
        print(f"  [清洗] 移除 {before - len(att)} 筆異常記錄")
    att["month_str"] = att["work_date"].dt.strftime("%Y-%m")
    return att, leaves


# ── 圖表函式（各自回傳 Figure）────────────────────────────────────────────────
def _chart_monthly_trend(att):
    data = att.groupby("month_str").size().reset_index(name="count")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(data["month_str"], data["count"], marker="o", color=BLUE_PAL[2], linewidth=2.2, markersize=6)
    ax.fill_between(range(len(data)), data["count"], alpha=0.12, color=BLUE_PAL[2])
    ax.set_xticks(range(len(data)))
    ax.set_xticklabels(data["month_str"], rotation=30, ha="right")
    ax.set_title("月度值勤人次趨勢", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("月份"); ax.set_ylabel("值勤筆數")
    fig.tight_layout(); return fig


def _chart_zone_bar(att):
    data = att["duty_zone"].value_counts().reset_index()
    data.columns = ["zone", "count"]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(data["zone"], data["count"], color=BLUE_PAL[:len(data)], edgecolor="white")
    ax.bar_label(bars, padding=4, fontsize=10)
    ax.set_title("值勤海域分布", fontsize=14, fontweight="bold", pad=10); ax.set_ylabel("值勤次數")
    fig.tight_layout(); return fig


def _chart_zone_sea_stacked(att):
    sea_order  = [s for s in ["平靜", "輕浪", "中浪", "大浪"] if s in att["sea_state"].values]
    zone_order = [z for z in ["港口", "近海", "外海"] if z in att["duty_zone"].values]
    if not sea_order or not zone_order:
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.set_title("各海域海況分布（資料不足）", fontsize=14, fontweight="bold")
        return fig
    pivot = (att.groupby(["duty_zone", "sea_state"]).size()
               .unstack(fill_value=0)
               .reindex(index=zone_order, columns=sea_order, fill_value=0)
               .astype(int))
    fig, ax = plt.subplots(figsize=(7, 5))
    pivot.plot(kind="bar", stacked=True, color=BLUE_PAL[:len(sea_order)],
               edgecolor="white", linewidth=0.6, ax=ax)
    ax.set_title("各海域海況分布", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("值勤海域"); ax.set_ylabel("值勤次數")
    ax.set_xticklabels(zone_order, rotation=0)
    ax.legend(title="海況", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout(); return fig


def _chart_vessel_count(att):
    data = att["vessel_id"].value_counts().sort_values()
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(data.index, data.values, color=BLUE_PAL[2], edgecolor="white")
    ax.bar_label(bars, padding=4, fontsize=9)
    ax.set_title("各船艦值勤次數", fontsize=14, fontweight="bold", pad=10); ax.set_xlabel("值勤次數")
    fig.tight_layout(); return fig


def _chart_hours_boxplot(att):
    sea_order = [s for s in ["平靜", "輕浪", "中浪", "大浪"] if s in att["sea_state"].values]
    fig, ax = plt.subplots(figsize=(8, 5))
    if att.empty or not sea_order:
        ax.set_title("各海況值勤時數分布（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    sns.boxplot(data=att, x="sea_state", y="hours", order=sea_order,
                palette=BLUE_PAL[:4], linewidth=1.2, ax=ax)
    ax.set_title("各海況值勤時數分布", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("海況"); ax.set_ylabel("值勤時數（小時）")
    fig.tight_layout(); return fig


def _chart_person_heatmap(att):
    fig, ax = plt.subplots(figsize=(8, 5))
    if att.empty:
        ax.set_title("人員月度出勤熱力圖（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    pivot = att.groupby(["full_name", "month_str"]).size().unstack(fill_value=0)
    if pivot.empty or pivot.shape[0] == 0 or pivot.shape[1] == 0:
        ax.set_title("人員月度出勤熱力圖（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    h = max(5, len(pivot) * 0.55); w = max(8, len(pivot.columns) * 1.3)
    fig.set_size_inches(w, h)
    sns.heatmap(pivot, annot=True, fmt="d", cmap="Blues",
                linewidths=0.5, linecolor="#e0e0e0",
                cbar_kws={"label": "值勤天數", "shrink": 0.7}, ax=ax)
    ax.set_title("人員月度出勤熱力圖", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("月份"); ax.set_ylabel("")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout(); return fig


def _chart_leave_trend(leaves):
    fig, ax = plt.subplots(figsize=(9, 4))
    approved = leaves[leaves["status"] == "approved"].copy()
    if approved.empty:
        ax.set_title("每月核准請假件數（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    approved["month_str"] = approved["date_from"].dt.strftime("%Y-%m")
    pivot = (approved.groupby(["month_str", "leave_type"]).size()
                     .unstack(fill_value=0)
                     .rename(columns={"personal": "事假", "sick": "病假", "other": "其他"}))
    if pivot.empty:
        ax.set_title("每月核准請假件數（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    pivot.plot(kind="bar", stacked=False, color=BLUE_PAL[:3], edgecolor="white", linewidth=0.6, ax=ax)
    ax.set_title("每月核准請假件數（依假別）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("月份"); ax.set_ylabel("件數")
    ax.set_xticklabels(pivot.index, rotation=30, ha="right")
    ax.legend(title="假別")
    fig.tight_layout(); return fig


# ── 圖 8：模擬 vs 觀測海況對照（需先執行 fetch_sea_data.py）────────────────────
def chart_sea_obs_comparison(output_dir: Path) -> str | None:
    """
    比較模擬值勤資料與 CWA 海象觀測資料的海況分布。
    若 sea_observations 表不存在或無資料，靜默跳過並回傳 None。
    """
    try:
        conn = get_connection()
        obs = pd.read_sql(
            "SELECT sea_state, COUNT(*) AS cnt FROM sea_observations GROUP BY sea_state",
            conn,
        )
        sim = pd.read_sql(
            "SELECT sea_state, COUNT(*) AS cnt FROM attendance "
            "WHERE sea_state IS NOT NULL GROUP BY sea_state",
            conn,
        )
        conn.close()
    except Exception:
        return None

    if obs.empty:
        return None

    sea_order = ["平靜", "輕浪", "中浪", "大浪"]

    obs_pct = obs.set_index("sea_state")["cnt"] / obs["cnt"].sum() * 100
    sim_pct = sim.set_index("sea_state")["cnt"] / sim["cnt"].sum() * 100

    df = pd.DataFrame({
        "觀測資料（CWA）": obs_pct.reindex(sea_order, fill_value=0),
        "模擬資料": sim_pct.reindex(sea_order, fill_value=0),
    })

    fig, ax = plt.subplots(figsize=(8, 5))
    df.plot(kind="bar", ax=ax, color=[BLUE_PAL[2], BLUE_PAL[4]],
            edgecolor="white", linewidth=0.6)
    ax.set_title("海況分布對照：觀測資料 vs 模擬資料", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("海況"); ax.set_ylabel("佔比 (%)")
    ax.set_xticklabels(sea_order, rotation=0)
    ax.legend(loc="upper right")
    fig.tight_layout()

    path = output_dir / "sea_obs_comparison.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(path)


# ── 統計摘要 ──────────────────────────────────────────────────────────────────
def _print_stats(att, leaves):
    print(f"\n{'─'*48}")
    print(f"  資料期間  : {att['work_date'].min().date()} ～ {att['work_date'].max().date()}")
    print(f"  值勤記錄  : {len(att):,} 筆  |  參與人員 {att['user_id'].nunique()} 人")
    print(f"  平均時數  : {att['hours'].mean():.2f} h  |  中位數 {att['hours'].median():.2f} h")
    print(f"  請假記錄  : {len(leaves)} 筆（核准 {(leaves['status']=='approved').sum()} 筆）")
    for col, label in [("duty_zone", "海域"), ("sea_state", "海況")]:
        print(f"\n  {label}分布：")
        for val, cnt in att[col].value_counts().items():
            print(f"    {val:4s}：{cnt:4d} 筆（{cnt/len(att)*100:.1f}%）")
    print(f"{'─'*48}\n")


# ── 獨立執行入口 ──────────────────────────────────────────────────────────────
def main():
    print("連線至資料庫...")
    conn = get_connection()
    att, leaves = _load_data(conn, None, None, None, None)
    conn.close()
    att, leaves = _clean(att, leaves)
    _print_stats(att, leaves)
    print("產生圖表...")
    generate_charts(OUTPUT_DIR)

    print("產生海象對照圖（需先執行 fetch_sea_data.py）...")
    cmp_path = chart_sea_obs_comparison(OUTPUT_DIR)
    if cmp_path:
        print(f"  ✔ sea_obs_comparison.png")
    else:
        print("  ℹ sea_observations 無資料，跳過對照圖")

    print(f"\n所有圖表已輸出至 {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
