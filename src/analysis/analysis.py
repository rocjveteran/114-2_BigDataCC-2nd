#!/usr/bin/env python3
"""
資料清洗、Pandas 統計分析、Matplotlib/Seaborn 圖表生成。
輸出 7 張 PNG 至 OUTPUT_DIR（與 PHP 端共用的 named volume）。

執行方式：
    docker compose run analysis python analysis.py
"""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless，無需 display
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import pandas as pd
import mysql.connector

# ── 連線設定 ──────────────────────────────────────────────────────────────────
DB = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "maritime_duty"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
}

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 中文字型（Noto CJK 由 Dockerfile 安裝）────────────────────────────────────
_cjk = [f.name for f in fm.fontManager.ttflist if "Noto" in f.name and "CJK" in f.name]
plt.rcParams["font.family"] = _cjk[:1] + ["DejaVu Sans"] if _cjk else ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 統一配色
BLUE_PAL = ["#0D47A1", "#1565C0", "#1976D2", "#1E88E5", "#42A5F5", "#90CAF9"]
sns.set_theme(style="whitegrid", palette=BLUE_PAL)


# ── 資料載入 ──────────────────────────────────────────────────────────────────
def load_data(conn):
    att = pd.read_sql(
        """
        SELECT a.att_id, a.user_id, u.full_name, u.role,
               a.work_date, a.check_in, a.check_out,
               a.duty_zone, a.sea_state, a.vessel_id
        FROM   attendance a
        JOIN   users u ON a.user_id = u.user_id
        WHERE  a.status = 'done'
        """,
        conn,
        parse_dates=["work_date", "check_in", "check_out"],
    )
    leaves = pd.read_sql(
        """
        SELECT l.leave_id, l.user_id, u.full_name,
               l.date_from, l.date_to, l.leave_type, l.status
        FROM   leaves l
        JOIN   users u ON l.user_id = u.user_id
        """,
        conn,
        parse_dates=["date_from", "date_to"],
    )
    users = pd.read_sql("SELECT user_id, username, full_name, role FROM users", conn)
    return att, leaves, users


# ── 資料清洗 ──────────────────────────────────────────────────────────────────
def clean_data(att: pd.DataFrame, leaves: pd.DataFrame):
    before = len(att)
    att = att.dropna(subset=["check_in", "check_out", "duty_zone", "sea_state", "vessel_id"])

    att = att.copy()
    att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600
    att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]

    dropped = before - len(att)
    if dropped:
        print(f"  [清洗] 移除 {dropped} 筆異常記錄（null 或時數超界）")

    att["month_str"]  = att["work_date"].dt.strftime("%Y-%m")
    att["year_month"] = att["work_date"].dt.to_period("M")

    return att, leaves


# ── 統計摘要 ──────────────────────────────────────────────────────────────────
def print_stats(att: pd.DataFrame, leaves: pd.DataFrame):
    print(f"\n{'─' * 48}")
    print(f"  資料期間  : {att['work_date'].min().date()} ～ {att['work_date'].max().date()}")
    print(f"  值勤記錄  : {len(att):,} 筆  |  參與人員 {att['user_id'].nunique()} 人")
    print(f"  平均時數  : {att['hours'].mean():.2f} h  |  中位數 {att['hours'].median():.2f} h")
    print(f"  請假記錄  : {len(leaves)} 筆（核准 {(leaves['status']=='approved').sum()} 筆）")
    print()
    for col, label in [("duty_zone", "海域"), ("sea_state", "海況")]:
        print(f"  {label}分布：")
        for val, cnt in att[col].value_counts().items():
            print(f"    {val:4s}：{cnt:4d} 筆（{cnt/len(att)*100:.1f}%）")
    print(f"{'─' * 48}\n")


# ── 圖 1：月度值勤人次趨勢 ────────────────────────────────────────────────────
def chart_monthly_trend(att: pd.DataFrame):
    data = att.groupby("month_str").size().reset_index(name="count")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(data["month_str"], data["count"], marker="o",
            color=BLUE_PAL[2], linewidth=2.2, markersize=6)
    ax.fill_between(range(len(data)), data["count"], alpha=0.12, color=BLUE_PAL[2])
    ax.set_xticks(range(len(data)))
    ax.set_xticklabels(data["month_str"], rotation=30, ha="right")
    ax.set_title("月度值勤人次趨勢", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("月份")
    ax.set_ylabel("值勤筆數")
    _save(fig, "monthly_trend.png")


# ── 圖 2：值勤海域分布（長條圖）──────────────────────────────────────────────
def chart_zone_bar(att: pd.DataFrame):
    data = att["duty_zone"].value_counts().reset_index()
    data.columns = ["zone", "count"]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(data["zone"], data["count"],
                  color=BLUE_PAL[:len(data)], edgecolor="white", linewidth=0.8)
    ax.bar_label(bars, padding=4, fontsize=10)
    ax.set_title("值勤海域分布", fontsize=14, fontweight="bold", pad=10)
    ax.set_ylabel("值勤次數")
    _save(fig, "zone_bar.png")


# ── 圖 3：各海域 × 海況堆疊長條圖 ────────────────────────────────────────────
def chart_zone_sea_stacked(att: pd.DataFrame):
    sea_order  = ["平靜", "輕浪", "中浪", "大浪"]
    zone_order = ["港口", "近海", "外海"]

    pivot = (
        att.groupby(["duty_zone", "sea_state"])
           .size()
           .unstack(fill_value=0)
           .reindex(index=zone_order, columns=sea_order, fill_value=0)
    )

    ax = pivot.plot(kind="bar", stacked=True, figsize=(7, 5),
                    color=BLUE_PAL[:4], edgecolor="white", linewidth=0.6)
    ax.set_title("各海域海況分布", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("值勤海域")
    ax.set_ylabel("值勤次數")
    ax.set_xticklabels(zone_order, rotation=0)
    ax.legend(title="海況", bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True)
    _save(ax.get_figure(), "zone_sea_stacked.png")


# ── 圖 4：各船艦值勤次數（水平長條）──────────────────────────────────────────
def chart_vessel_count(att: pd.DataFrame):
    data = att["vessel_id"].value_counts().sort_values()

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(data.index, data.values,
                   color=BLUE_PAL[2], edgecolor="white", linewidth=0.6)
    ax.bar_label(bars, padding=4, fontsize=9)
    ax.set_title("各船艦值勤次數", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("值勤次數")
    _save(fig, "vessel_count.png")


# ── 圖 5：各海況值勤時數箱型圖 ───────────────────────────────────────────────
def chart_hours_boxplot(att: pd.DataFrame):
    sea_order = [s for s in ["平靜", "輕浪", "中浪", "大浪"]
                 if s in att["sea_state"].unique()]

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=att, x="sea_state", y="hours", order=sea_order,
                palette=BLUE_PAL[:4], linewidth=1.2, ax=ax)
    ax.set_title("各海況值勤時數分布", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("海況")
    ax.set_ylabel("值勤時數（小時）")
    _save(fig, "hours_boxplot.png")


# ── 圖 6：人員月度出勤熱力圖 ─────────────────────────────────────────────────
def chart_person_heatmap(att: pd.DataFrame):
    pivot = att.groupby(["full_name", "month_str"]).size().unstack(fill_value=0)

    h = max(5, len(pivot) * 0.55)
    w = max(8, len(pivot.columns) * 1.3)
    fig, ax = plt.subplots(figsize=(w, h))
    sns.heatmap(pivot, annot=True, fmt="d", cmap="Blues",
                linewidths=0.5, linecolor="#e0e0e0",
                cbar_kws={"label": "值勤天數", "shrink": 0.7}, ax=ax)
    ax.set_title("人員月度出勤熱力圖", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("月份")
    ax.set_ylabel("")
    plt.xticks(rotation=30, ha="right")
    _save(fig, "person_heatmap.png")


# ── 圖 7：每月核准請假件數（依假別堆疊）──────────────────────────────────────
def chart_leave_trend(leaves: pd.DataFrame):
    approved = leaves[leaves["status"] == "approved"].copy()
    approved["month_str"] = approved["date_from"].dt.strftime("%Y-%m")

    pivot = (
        approved.groupby(["month_str", "leave_type"])
                .size()
                .unstack(fill_value=0)
                .rename(columns={"personal": "事假", "sick": "病假", "other": "其他"})
    )

    ax = pivot.plot(kind="bar", stacked=False, figsize=(9, 4),
                    color=BLUE_PAL[:3], edgecolor="white", linewidth=0.6)
    ax.set_title("每月核准請假件數（依假別）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("月份")
    ax.set_ylabel("件數")
    ax.set_xticklabels(pivot.index, rotation=30, ha="right")
    ax.legend(title="假別", frameon=True)
    _save(ax.get_figure(), "leave_trend.png")


# ── 存檔輔助 ──────────────────────────────────────────────────────────────────
def _save(fig: plt.Figure, name: str):
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✔ {name}")


# ── 入口 ──────────────────────────────────────────────────────────────────────
def main():
    print("連線至資料庫...")
    conn = mysql.connector.connect(**DB)

    print("載入資料...")
    att, leaves, users = load_data(conn)
    conn.close()

    print("清洗資料...")
    att, leaves = clean_data(att, leaves)

    print_stats(att, leaves)

    print("產生圖表...")
    chart_monthly_trend(att)
    chart_zone_bar(att)
    chart_zone_sea_stacked(att)
    chart_vessel_count(att)
    chart_hours_boxplot(att)
    chart_person_heatmap(att)
    chart_leave_trend(leaves)

    print(f"\n所有圖表已輸出至 {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
