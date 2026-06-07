#!/usr/bin/env python3
"""
資料清洗、Pandas 統計分析、Matplotlib/Seaborn 圖表生成。
可作為獨立腳本執行，也可由 app.py（Gradio）呼叫 generate_charts()。

執行方式：
    docker compose run analysis python analysis.py
"""

import os
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import pandas as pd
import numpy as np
from scipy import stats as sps
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

BLUE_PAL    = ["#0D47A1", "#1565C0", "#1976D2", "#1E88E5", "#42A5F5", "#90CAF9"]
# 對齊 schema.sql 的 ENUM 定義與由弱到強的自然排序（圖表 x 軸 / 熱力圖列序依此）
SEA_STATES  = ["平靜", "輕浪", "中浪", "大浪"]
DUTY_ZONES  = ["港口", "近海", "外海"]
LEAVE_TYPES = {"personal": "事假", "sick": "病假", "other": "其他"}
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

    # 即時海況觀測（供地圖 / 靜態示意圖 / 決策建議使用）
    sea_obs = _load_sea_observations()

    paths = []
    for fn, chart_fn in [
        (f"{prefix}monthly_trend.png",    lambda: _chart_monthly_trend(att)),
        (f"{prefix}zone_bar.png",         lambda: _chart_zone_bar(att)),
        (f"{prefix}zone_sea_stacked.png", lambda: _chart_zone_sea_stacked(att)),
        (f"{prefix}vessel_count.png",     lambda: _chart_vessel_count(att)),
        (f"{prefix}hours_boxplot.png",    lambda: _chart_hours_boxplot(att)),
        (f"{prefix}person_heatmap.png",   lambda: _chart_person_heatmap(att)),
        (f"{prefix}leave_trend.png",      lambda: _chart_leave_trend(leaves)),
        (f"{prefix}hours_heatmap.png",    lambda: _chart_hours_heatmap(att)),
        (f"{prefix}anomaly_detect.png",   lambda: _chart_anomaly_detect(att)),
        (f"{prefix}weekday_pattern.png",  lambda: _chart_weekday_pattern(att)),
        (f"{prefix}vessel_pareto.png",    lambda: _chart_vessel_pareto(att)),
        (f"{prefix}forecast_duty.png",      lambda: _chart_forecast_duty(att)),
        (f"{prefix}correlation_matrix.png", lambda: _chart_correlation(att)),
        (f"{prefix}regression_coef.png",    lambda: _chart_regression_coef(att)),
        (f"{prefix}crew_clusters.png",      lambda: _chart_crew_clusters(att)),
        (f"{prefix}markov_heatmap.png",     lambda: _chart_markov_heatmap(att)),
        (f"{prefix}zone_map_static.png",    lambda: _chart_zone_map_static(att, sea_obs)),
        (f"{prefix}feature_importance.png", lambda: _chart_feature_importance(att)),
        (f"{prefix}fatigue.png",            lambda: _chart_fatigue(att)),
        (f"{prefix}fairness_lorenz.png",    lambda: _chart_fairness_lorenz(att)),
        (f"{prefix}vessel_availability.png",lambda: _chart_vessel_availability(att)),
    ]:
        fig = chart_fn()
        path = out / fn
        fig.savefig(path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"  ✔ {fn}")
        paths.append(str(path))

    # 寫統計檢定報告（PHP 儀表板會讀此檔）
    stats_data = compute_stats(att, leaves)
    stats_path = out / f"{prefix}stats_summary.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)
    print(f"  ✔ {stats_path.name}")

    # 寫勤務決策建議（PHP 儀表板讀 recommendations.json）
    rec_data = compute_recommendations(att, sea_obs=sea_obs, output_dir=out)
    rec_path = out / f"{prefix}recommendations.json"
    with open(rec_path, "w", encoding="utf-8") as f:
        json.dump(rec_data, f, ensure_ascii=False, indent=2)
    print(f"  ✔ {rec_path.name}")

    # 產生 Folium 互動海域地圖（duty_map.html，供 PHP iframe 嵌入）
    build_duty_map(att, out, sea_obs=sea_obs)

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
    sea_order  = [s for s in SEA_STATES if s in att["sea_state"].values]
    zone_order = [z for z in DUTY_ZONES if z in att["duty_zone"].values]
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
    sea_order = [s for s in SEA_STATES if s in att["sea_state"].values]
    fig, ax = plt.subplots(figsize=(8, 5))
    if att.empty or not sea_order:
        ax.set_title("各海況值勤時數分布（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    sns.boxplot(data=att, x="sea_state", y="hours", order=sea_order,
                hue="sea_state", palette=BLUE_PAL[:4], legend=False,
                linewidth=1.2, ax=ax)
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
                     .rename(columns=LEAVE_TYPES))
    if pivot.empty:
        ax.set_title("每月核准請假件數（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    pivot.plot(kind="bar", stacked=False, color=BLUE_PAL[:3], edgecolor="white", linewidth=0.6, ax=ax)
    ax.set_title("每月核准請假件數（依假別）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("月份"); ax.set_ylabel("件數")
    ax.set_xticklabels(pivot.index, rotation=30, ha="right")
    ax.legend(title="假別")
    fig.tight_layout(); return fig


# ── 圖 8：海域 × 海況 平均工時熱力圖 ─────────────────────────────────────────
def _chart_hours_heatmap(att):
    """揭露兩個維度的交互效應：同樣海況下，不同海域工時差多少？"""
    sea_order  = [s for s in SEA_STATES if s in att["sea_state"].values]
    zone_order = [z for z in DUTY_ZONES if z in att["duty_zone"].values]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if att.empty or not sea_order or not zone_order:
        ax.set_title("海域×海況平均工時（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    pivot = (att.groupby(["duty_zone", "sea_state"])["hours"].mean()
                .unstack(fill_value=np.nan)
                .reindex(index=zone_order, columns=sea_order))
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="YlOrRd",
                linewidths=0.6, linecolor="#ffffff",
                cbar_kws={"label": "平均工時（小時）"}, ax=ax)
    ax.set_title("海域 × 海況：平均工時交互效應", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("海況"); ax.set_ylabel("值勤海域")
    fig.tight_layout(); return fig


# ── 圖 9：異常值勤偵測（Z-score）─────────────────────────────────────────────
def _chart_anomaly_detect(att):
    """以 Z-score > 2 標示異常工時，視覺化離群點分布。"""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    if att.empty or len(att) < 10:
        ax.set_title("異常值勤偵測（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    z = np.abs(sps.zscore(att["hours"]))
    normal = att[z <= 2]; outlier = att[z > 2]
    ax.scatter(normal["work_date"], normal["hours"],
               s=22, alpha=0.45, color=BLUE_PAL[3], label=f"正常 ({len(normal)})", edgecolors="none")
    if not outlier.empty:
        ax.scatter(outlier["work_date"], outlier["hours"],
                   s=70, alpha=0.95, color="#c0001e", marker="X",
                   label=f"異常 |z|>2 ({len(outlier)})", edgecolors="white", linewidth=0.8)
    mean = att["hours"].mean(); std = att["hours"].std()
    ax.axhline(mean, color="#888", linestyle="--", linewidth=1, alpha=0.6, label=f"平均 {mean:.2f}h")
    ax.axhspan(mean - 2*std, mean + 2*std, color="#888", alpha=0.06, label="±2σ 區間")
    ax.set_title("異常值勤偵測（Z-score 法）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("值勤日期"); ax.set_ylabel("值勤時數（小時）")
    ax.legend(loc="best", framealpha=0.9, fontsize=10)
    fig.autofmt_xdate(); fig.tight_layout(); return fig


# ── 圖 10：週幾出勤模式 ──────────────────────────────────────────────────────
def _chart_weekday_pattern(att):
    """分析星期效應：哪天人力最忙、哪天最閒？"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if att.empty:
        ax.set_title("週幾出勤模式（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    wd_zh = ["一", "二", "三", "四", "五", "六", "日"]
    att2 = att.copy()
    att2["weekday"] = att2["work_date"].dt.weekday
    counts = att2.groupby("weekday").size().reindex(range(7), fill_value=0)
    hours_avg = att2.groupby("weekday")["hours"].mean().reindex(range(7))
    x = np.arange(7)
    bars = ax.bar(x, counts.values, color=BLUE_PAL[:7], edgecolor="white", width=0.65)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(wd_zh)
    ax.set_title("週幾出勤模式：值勤次數 + 平均工時", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("星期"); ax.set_ylabel("值勤次數")
    ax2 = ax.twinx()
    ax2.plot(x, hours_avg.values, color="#c0001e", marker="o", linewidth=2, markersize=7, label="平均工時")
    ax2.set_ylabel("平均工時（小時）", color="#c0001e")
    ax2.tick_params(axis="y", labelcolor="#c0001e")
    ax2.grid(False)
    fig.tight_layout(); return fig


# ── 圖 11：船艦利用率 Pareto 圖 ───────────────────────────────────────────────
def _chart_vessel_pareto(att):
    """80/20 法則：少數船艦扛多數工作量？"""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    if att.empty:
        ax.set_title("船艦使用 Pareto（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    counts = att["vessel_id"].value_counts().sort_values(ascending=False)
    cum_pct = counts.cumsum() / counts.sum() * 100
    x = np.arange(len(counts))
    bars = ax.bar(x, counts.values, color=BLUE_PAL[2], edgecolor="white", width=0.75)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(counts.index, rotation=30, ha="right")
    ax.set_title("船艦使用 Pareto 圖（80/20 法則檢視）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("船艦"); ax.set_ylabel("值勤次數")
    ax2 = ax.twinx()
    ax2.plot(x, cum_pct.values, color="#c96442", marker="o", linewidth=2, markersize=6, label="累積佔比")
    ax2.axhline(80, color="#888", linestyle="--", linewidth=1, alpha=0.7)
    ax2.text(len(counts) - 0.5, 82, "80%", color="#666", fontsize=10, ha="right")
    ax2.set_ylabel("累積佔比 (%)", color="#c96442")
    ax2.set_ylim(0, 105)
    ax2.tick_params(axis="y", labelcolor="#c96442")
    ax2.grid(False)
    fig.tight_layout(); return fig


# ── 進階分析：預測、相關、建模、分群 ─────────────────────────────────────────
# 序位映射（海況由弱到強、海域由近到遠），供相關 / 迴歸 / 分群之數值化使用。
SEA_RANK  = {s: i + 1 for i, s in enumerate(SEA_STATES)}   # 平靜=1 … 大浪=4
ZONE_RANK = {z: i + 1 for i, z in enumerate(DUTY_ZONES)}   # 港口=1 … 外海=3


def _chart_forecast_duty(att):
    """圖 12：值勤量時間序列預測 — 週彙整 + 線性趨勢外推未來 4 週（含 95% 預測區間）。"""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    if att.empty or att["work_date"].nunique() < 14:
        ax.set_title("值勤量時間序列預測（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    weekly = att.set_index("work_date").resample("W")["att_id"].count()
    weekly = weekly[weekly > 0]
    # 丟棄尾端「尚未結束的當週」（與今天比對該週結束之週日），避免不完整資料造成斷崖假象與趨勢偏誤
    today = pd.Timestamp.today().normalize()
    if len(weekly) >= 2 and weekly.index[-1].normalize() > today:
        weekly = weekly.iloc[:-1]
    if len(weekly) < 6:
        ax.set_title("值勤量時間序列預測（週資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    y = weekly.values.astype(float)
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    fit = slope * x + intercept
    resid_std = np.sqrt(((y - fit) ** 2).sum() / max(len(y) - 2, 1))
    H = 4
    xf = np.arange(len(y), len(y) + H)
    yf = slope * xf + intercept
    band = 1.96 * resid_std
    last = weekly.index[-1]
    future = [last + pd.Timedelta(weeks=i + 1) for i in range(H)]
    ax.plot(weekly.index, y, marker="o", color=BLUE_PAL[2], lw=2, markersize=5, label="歷史週值勤量")
    ax.plot(weekly.index, fit, color=BLUE_PAL[4], ls="--", lw=1.4, label=f"線性趨勢（{slope:+.1f}/週）")
    ax.plot(future, yf, marker="s", color="#c96442", lw=2, markersize=6, label="預測（未來 4 週）")
    ax.fill_between(future, yf - band, yf + band, color="#c96442", alpha=0.15, label="95% 預測區間")
    ax.axvline(last, color="#999", ls=":", lw=1)
    ax.set_title("值勤量時間序列預測（週彙整 + 線性外推）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("週"); ax.set_ylabel("每週值勤筆數")
    ax.legend(fontsize=9, loc="best", framealpha=0.9)
    fig.autofmt_xdate(); fig.tight_layout(); return fig


def _chart_correlation(att):
    """圖 13：特徵相關矩陣（Spearman）— 工時與海況 / 海域 / 時間特徵的關聯強度與方向。"""
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    if att.empty or len(att) < 20:
        ax.set_title("特徵相關矩陣（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    feat = pd.DataFrame({
        "值勤時數": att["hours"].values,
        "海況等級": att["sea_state"].map(SEA_RANK).values,
        "海域距岸": att["duty_zone"].map(ZONE_RANK).values,
        "星期":     att["work_date"].dt.weekday.values,
        "上工時刻": (att["check_in"].dt.hour + att["check_in"].dt.minute / 60.0).values,
        "月份":     att["work_date"].dt.month.values,
    }).dropna()
    corr = feat.corr(method="spearman")
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                vmin=-1, vmax=1, linewidths=0.6, linecolor="#ffffff",
                square=True, cbar_kws={"label": "Spearman ρ", "shrink": 0.8}, ax=ax)
    ax.set_title("特徵相關矩陣（Spearman 等級相關）", fontsize=14, fontweight="bold", pad=10)
    plt.xticks(rotation=30, ha="right"); plt.yticks(rotation=0)
    fig.tight_layout(); return fig


def _fit_hours_ols(att):
    """以標準化多元線性迴歸（OLS）找出工時驅動因子。回傳 (r2, {因子: 標準化係數}) 或 None。"""
    if att is None or att.empty or len(att) < 30:
        return None
    X = pd.DataFrame({
        "海況等級": att["sea_state"].map(SEA_RANK),
        "海域距岸": att["duty_zone"].map(ZONE_RANK),
        "星期":     att["work_date"].dt.weekday,
        "上工時刻": att["check_in"].dt.hour + att["check_in"].dt.minute / 60.0,
    }).astype(float)
    y = att["hours"].astype(float).values
    sd = X.std(ddof=0)
    if (sd == 0).any() or np.std(y) == 0:
        return None
    Xs = (X - X.mean()) / sd
    A = np.column_stack([np.ones(len(Xs)), Xs.values])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    yhat = A @ beta
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return r2, dict(zip(X.columns, beta[1:]))


def _chart_regression_coef(att):
    """圖 14：工時驅動因子 — 標準化 OLS 迴歸係數（正=拉長工時、負=縮短工時）。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    res = _fit_hours_ols(att)
    if res is None:
        ax.set_title("工時驅動因子迴歸（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    r2, coefs = res
    items = sorted(coefs.items(), key=lambda kv: kv[1])
    names = [k for k, _ in items]
    vals  = [v for _, v in items]
    colors = ["#c0001e" if v < 0 else BLUE_PAL[2] for v in vals]
    bars = ax.barh(names, vals, color=colors, edgecolor="white")
    ax.bar_label(bars, fmt="%+.3f", padding=4, fontsize=9)
    ax.axvline(0, color="#444", lw=1)
    ax.set_title(f"工時驅動因子（標準化 OLS 迴歸，R² = {r2:.3f}）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("標準化迴歸係數（對單次工時的邊際影響）")
    fig.tight_layout(); return fig


def _chart_crew_clusters(att):
    """圖 15：人員值勤模式分群（K-means, k=3）— 平均工時 × 外海暴露比例，辨識輪值型態。"""
    fig, ax = plt.subplots(figsize=(8, 5.5))
    if att.empty:
        ax.set_title("人員值勤模式分群（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    g = att.groupby("full_name")
    prof = pd.DataFrame({
        "avg_hours":   g["hours"].mean(),
        "outer_ratio": g["duty_zone"].apply(lambda s: (s == "外海").mean()),
        "count":       g.size(),
    }).dropna()
    if len(prof) < 4:
        ax.set_title("人員值勤模式分群（人數不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    feats = prof[["avg_hours", "outer_ratio", "count"]].values.astype(float)
    mu = feats.mean(axis=0); sd = feats.std(axis=0); sd[sd == 0] = 1.0
    w = (feats - mu) / sd
    k = min(3, len(prof))
    try:
        from scipy.cluster.vq import kmeans2
        np.random.seed(42)
        _, labels = kmeans2(w, k, minit="++")
    except Exception:
        labels = np.zeros(len(prof), dtype=int)
    palette = ["#1565C0", "#c96442", "#3a6b4a", "#8a5a0c"]
    for cid in range(int(labels.max()) + 1 if len(labels) else 0):
        m = labels == cid
        if not m.any():
            continue
        ax.scatter(prof["avg_hours"].values[m], prof["outer_ratio"].values[m] * 100,
                   s=prof["count"].values[m] * 1.4 + 50, color=palette[cid % len(palette)],
                   edgecolors="white", linewidth=1.2, alpha=0.9, label=f"群 {cid + 1}")
    for name, row in prof.iterrows():
        ax.annotate(str(name), (row["avg_hours"], row["outer_ratio"] * 100),
                    fontsize=8, ha="center", va="bottom",
                    xytext=(0, 7), textcoords="offset points", color="#444")
    ax.set_title("人員值勤模式分群（K-means, k=3）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("平均單次工時（小時）"); ax.set_ylabel("外海值勤比例 (%)")
    ax.legend(fontsize=9, loc="best", framealpha=0.9, title="型態分群")
    ax.text(0.01, 0.98, "點大小 = 值勤次數", transform=ax.transAxes,
            ha="left", va="top", fontsize=8, color="#888")
    fig.tight_layout(); return fig


# ── 圖 16：Markov 海況轉移矩陣 + 未來 7 天預測 ───────────────────────────────

def _compute_markov_transition(att: pd.DataFrame) -> np.ndarray:
    """以 (今日海況 → 明日海況) 轉移次數計算 4×4 機率矩陣。"""
    n = len(SEA_STATES)
    idx = {s: i for i, s in enumerate(SEA_STATES)}
    seq = att.sort_values("work_date")["sea_state"].dropna().tolist()
    counts = np.zeros((n, n))
    for a, b in zip(seq[:-1], seq[1:]):
        if a in idx and b in idx:
            counts[idx[a]][idx[b]] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    return counts / row_sums


def _chart_markov_heatmap(att: pd.DataFrame):
    """圖 16：Markov 轉移機率矩陣（左）＋ 未來 7 天海況預測機率熱力圖（右）。"""
    trans = _compute_markov_transition(att)
    states = SEA_STATES

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    sns.heatmap(trans, annot=True, fmt=".2f", cmap="Blues",
                xticklabels=states, yticklabels=states,
                ax=ax1, vmin=0, vmax=1,
                cbar_kws={"label": "轉移機率"})
    ax1.set_title("海況 Markov 轉移機率矩陣")
    ax1.set_xlabel("下一日海況")
    ax1.set_ylabel("當日海況")

    last_valid = att.sort_values("work_date")["sea_state"].dropna()
    if last_valid.empty:
        ax2.set_title("（無資料）")
        fig.tight_layout()
        return fig

    last_idx = SEA_STATES.index(last_valid.iloc[-1])
    probs = np.zeros((8, len(states)))
    probs[0, last_idx] = 1.0
    for d in range(1, 8):
        probs[d] = probs[d - 1] @ trans

    prob_df = pd.DataFrame(probs[1:], columns=states,
                           index=[f"D+{i + 1}" for i in range(7)])
    sns.heatmap(prob_df.T, annot=True, fmt=".2f", cmap="YlOrRd",
                ax=ax2, vmin=0, vmax=1,
                cbar_kws={"label": "機率"})
    ax2.set_title("未來 7 天海況預測機率（Markov）")
    ax2.set_xlabel("預測天數")
    ax2.set_ylabel("海況")

    fig.tight_layout()
    return fig


# ── 即時海況觀測載入（sea_observations，由 fetch_sea_data.py 產生）─────────────
def _load_sea_observations() -> pd.DataFrame:
    """讀取 CWA 浮標/季節性模擬海象觀測資料。表不存在時回傳空 DataFrame。"""
    try:
        conn = get_connection()
        df = pd.read_sql(
            "SELECT station_id, station_name, obs_date, wave_height, wave_period, "
            "sea_temp, sea_state, data_source FROM sea_observations",
            conn, parse_dates=["obs_date"],
        )
        conn.close()
    except Exception as e:
        print(f"[analysis] sea_observations 載入跳過：{e}")
        return pd.DataFrame()
    for c in ["station_name", "sea_state", "data_source"]:
        if c in df.columns:
            df[c] = df[c].apply(lambda x: x.decode("utf-8") if isinstance(x, bytes) else x)
    return df


def latest_sea_now(sea_obs: pd.DataFrame) -> dict | None:
    """取最新一日的全站平均波高與代表海況，供儀表板「現在海況」橫幅使用。"""
    if sea_obs is None or sea_obs.empty:
        return None
    last_date = sea_obs["obs_date"].max()
    day = sea_obs[sea_obs["obs_date"] == last_date]
    wave = float(day["wave_height"].dropna().mean()) if day["wave_height"].notna().any() else None
    temp = float(day["sea_temp"].dropna().mean()) if day["sea_temp"].notna().any() else None
    # 代表海況：當日最嚴重者（風險取向）
    ranks = day["sea_state"].dropna().map(SEA_RANK)
    sea_state = SEA_STATES[int(ranks.max()) - 1] if len(ranks) else None
    src = day["data_source"].iloc[0] if "data_source" in day.columns and len(day) else None
    return {
        "obs_date": str(last_date.date()),
        "wave_height": round(wave, 2) if wave is not None else None,
        "sea_temp": round(temp, 1) if temp is not None else None,
        "sea_state": sea_state,
        "stations": int(day["station_id"].nunique()),
        "data_source": src,
    }


# ── 地理座標（台灣周邊海域，供 Folium 互動地圖）──────────────────────────────
ZONE_GEO = {
    "港口": {"center": [25.12, 121.74], "color": "#2e7d32",
             "poly": [[25.22, 121.66], [25.22, 121.84], [25.02, 121.84], [25.02, 121.66]]},
    "近海": {"center": [24.50, 122.25], "color": "#ef6c00",
             "poly": [[25.35, 121.90], [25.35, 122.65], [23.55, 122.65], [23.55, 121.90]]},
    "外海": {"center": [23.90, 123.25], "color": "#c0001e",
             "poly": [[25.45, 122.70], [25.45, 124.10], [22.40, 124.10], [22.40, 122.70]]},
}

# CWA 浮標站座標（與 fetch_sea_data.py STATIONS 對應）
BUOY_GEO = {
    "彭佳嶼":   [25.63, 122.07],
    "花蓮外海": [23.98, 121.62],
    "東沙島":   [20.70, 116.72],
    "鞍部浮標": [25.18, 121.53],
}

# 船艦母港對應海域（MAR-001 ~ MAR-008）
VESSEL_ZONE = {
    "MAR-001": "港口", "MAR-002": "港口", "MAR-003": "近海", "MAR-004": "近海",
    "MAR-005": "近海", "MAR-006": "外海", "MAR-007": "外海", "MAR-008": "外海",
}


def build_duty_map(att, output_dir, sea_obs=None) -> str | None:
    """產生 Folium 互動海域地圖（duty_map.html）：海域多邊形 + 船艦 + 浮標 + 值勤熱力圖。"""
    try:
        import folium
        from folium.plugins import HeatMap
    except Exception as e:
        print(f"[analysis] folium 未安裝，跳過互動地圖：{e}")
        return None

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    np.random.seed(42)

    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=30)
    recent = att[att["work_date"] >= cutoff] if (att is not None and not att.empty) else att
    if recent is None or len(recent) < 5:
        recent = att if att is not None else pd.DataFrame()

    sea_now = latest_sea_now(sea_obs)

    m = folium.Map(location=[24.0, 121.8], zoom_start=7,
                   tiles="OpenStreetMap", control_scale=True)

    # 海域多邊形 + popup 統計
    heat_pts = []
    for zone, geo in ZONE_GEO.items():
        zd = recent[recent["duty_zone"] == zone] if not recent.empty else recent
        cnt = int(len(zd)) if zd is not None else 0
        rough = float((zd["sea_state"] == "大浪").mean() * 100) if cnt else 0.0
        avgh = float(zd["hours"].mean()) if cnt else 0.0
        popup_html = (
            f"<div style='font-family:sans-serif;font-size:13px;'>"
            f"<b style='font-size:14px;'>{zone}海域</b><br>"
            f"近 30 天值勤：<b>{cnt}</b> 次<br>"
            f"大浪比例：<b>{rough:.0f}%</b><br>"
            f"平均工時：<b>{avgh:.1f}</b> h</div>"
        )
        folium.Polygon(
            locations=geo["poly"], color=geo["color"], weight=2,
            fill=True, fill_color=geo["color"], fill_opacity=0.16,
            popup=folium.Popup(popup_html, max_width=220), tooltip=f"{zone}（{cnt} 次）",
        ).add_to(m)
        cy, cx = geo["center"]
        folium.map.Marker(
            [cy, cx],
            icon=folium.DivIcon(html=(
                f"<div style='font-size:12px;font-weight:700;color:{geo['color']};"
                f"text-shadow:0 0 3px #fff,0 0 3px #fff;white-space:nowrap;'>{zone} {cnt}</div>"
            )),
        ).add_to(m)
        for _ in range(min(cnt, 90)):
            heat_pts.append([cy + np.random.uniform(-0.16, 0.16),
                             cx + np.random.uniform(-0.22, 0.22)])

    if heat_pts:
        HeatMap(heat_pts, radius=17, blur=23, min_opacity=0.25).add_to(m)

    # 船艦 marker（落於母港海域中心附近）
    vessels = sorted(recent["vessel_id"].dropna().unique()) if (recent is not None and not recent.empty) else list(VESSEL_ZONE)
    for v in vessels:
        zone = VESSEL_ZONE.get(v, "近海")
        cy, cx = ZONE_GEO[zone]["center"]
        vc = int((recent["vessel_id"] == v).sum()) if not recent.empty else 0
        folium.Marker(
            [cy + np.random.uniform(-0.12, 0.12), cx + np.random.uniform(-0.18, 0.18)],
            tooltip=f"{v}（{zone}・近30天 {vc} 次）",
            icon=folium.Icon(color="blue", icon="ship", prefix="fa"),
        ).add_to(m)

    # CWA 浮標站 marker（顯示最新觀測波高）
    obs_by_station = {}
    if sea_obs is not None and not sea_obs.empty:
        last = sea_obs.sort_values("obs_date").groupby("station_name").tail(1)
        for _, r in last.iterrows():
            obs_by_station[r["station_name"]] = r
    for name, (lat, lon) in BUOY_GEO.items():
        info = obs_by_station.get(name)
        if info is not None:
            wh = info.get("wave_height")
            ss = info.get("sea_state")
            src = "CWA 觀測" if info.get("data_source") == "cwa_api" else "季節模擬"
            tip = f"浮標 {name}｜波高 {wh} m｜{ss}｜{src}"
        else:
            tip = f"浮標 {name}"
        folium.CircleMarker(
            [lat, lon], radius=7, color="#0d47a1", weight=2,
            fill=True, fill_color="#42a5f5", fill_opacity=0.9,
            tooltip=tip,
        ).add_to(m)

    # 圖例 + 即時海況卡
    now_html = ""
    if sea_now:
        now_html = (
            f"<hr style='margin:6px 0;border:none;border-top:1px solid #ddd;'>"
            f"<b>即時海況</b>（{sea_now['obs_date']}）<br>"
            f"代表海況：{sea_now['sea_state'] or '—'}<br>"
            f"平均波高：{sea_now['wave_height'] if sea_now['wave_height'] is not None else '—'} m"
        )
    legend = folium.Element(f"""
    <div style="position:fixed;bottom:24px;left:24px;z-index:9999;background:#fff;
                padding:10px 14px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.18);
                font-family:sans-serif;font-size:12.5px;line-height:1.6;">
      <b>海事勤務海域圖</b><br>
      <span style="color:#2e7d32;">■</span> 港口
      <span style="color:#ef6c00;">■</span> 近海
      <span style="color:#c0001e;">■</span> 外海<br>
      <span style="color:#0d47a1;">●</span> CWA 浮標站　🚢 船艦
      {now_html}
    </div>""")
    m.get_root().html.add_child(legend)

    path = out / "duty_map.html"
    m.save(str(path))
    print(f"  ✔ duty_map.html")
    return str(path)


def _chart_zone_map_static(att, sea_obs=None):
    """圖：海域配置示意圖（靜態，供 Gradio / README 截圖）— 海域框、船艦、浮標於經緯度上。"""
    fig, ax = plt.subplots(figsize=(8.5, 7))
    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=30)
    recent = att[att["work_date"] >= cutoff] if (att is not None and not att.empty) else att
    if recent is None or len(recent) < 5:
        recent = att if att is not None else pd.DataFrame()

    # 海域矩形
    for zone, geo in ZONE_GEO.items():
        poly = np.array(geo["poly"])
        lats, lons = poly[:, 0], poly[:, 1]
        cnt = int((recent["duty_zone"] == zone).sum()) if not recent.empty else 0
        rough = float((recent[recent["duty_zone"] == zone]["sea_state"] == "大浪").mean() * 100) if cnt else 0
        ax.fill(np.append(lons, lons[0]), np.append(lats, lats[0]),
                color=geo["color"], alpha=0.14, zorder=1)
        ax.plot(np.append(lons, lons[0]), np.append(lats, lats[0]),
                color=geo["color"], lw=1.8, zorder=2)
        cy, cx = geo["center"]
        ax.annotate(f"{zone}\n{cnt} 次・大浪 {rough:.0f}%", (cx, cy),
                    color=geo["color"], fontsize=11, fontweight="bold",
                    ha="center", va="center", zorder=5)

    # 浮標站
    for name, (lat, lon) in BUOY_GEO.items():
        if lat < 22:  # 東沙過遠，標註但壓在邊界附近避免壓縮主圖
            continue
        ax.scatter(lon, lat, s=90, marker="o", color="#42a5f5",
                   edgecolors="#0d47a1", linewidth=1.5, zorder=6)
        ax.annotate(name, (lon, lat), fontsize=8.5, color="#0d47a1",
                    xytext=(0, 8), textcoords="offset points", ha="center", zorder=6)

    # 台灣本島粗略輪廓參考點
    ax.scatter(121.0, 23.8, s=1400, marker="*", color="#cfcabb",
               alpha=0.5, zorder=0, label="台灣本島")
    ax.annotate("台灣", (121.0, 23.8), fontsize=12, color="#8a8472",
                ha="center", va="center", zorder=1)

    ax.set_xlim(120.4, 124.3); ax.set_ylim(22.2, 26.0)
    ax.set_xlabel("經度 (°E)"); ax.set_ylabel("緯度 (°N)")
    ax.set_title("海事勤務海域配置示意圖（近 30 天）", fontsize=14, fontweight="bold", pad=10)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


# ── scikit-learn 海況預測模型 ─────────────────────────────────────────────────
def _build_supervised(att):
    """建立每日海況監督式資料集：以今日 + 近日特徵預測『明日是否惡劣海況（中浪以上）』。"""
    if att is None or att.empty:
        return None
    daily = (att.assign(_d=att["work_date"].dt.normalize())
                .groupby("_d")
                .agg(sea_rank=("sea_state", lambda s: s.map(SEA_RANK).mean()),
                     offshore=("duty_zone", lambda z: (z == "外海").mean()))
                .sort_index())
    if len(daily) < 30:
        return None
    rough_today = (daily["sea_rank"] >= 2.5).astype(int)
    df = pd.DataFrame(index=daily.index)
    df["today"]    = daily["sea_rank"]
    df["lag1"]     = daily["sea_rank"].shift(1)
    df["lag2"]     = daily["sea_rank"].shift(2)
    df["roll3"]    = daily["sea_rank"].rolling(3).mean()
    df["offshore"] = daily["offshore"]
    df["month"]    = daily.index.month
    df["weekday"]  = daily.index.weekday
    df["target"]   = rough_today.shift(-1)   # 明日是否惡劣
    feat_cols = ["today", "lag1", "lag2", "roll3", "offshore", "month", "weekday"]
    last_feat = df[feat_cols].iloc[[-1]].dropna()   # 最新一日（target=NaN）供預測明日
    train = df.dropna()
    return feat_cols, train, last_feat


FEATURE_LABELS = {
    "today": "今日海況", "lag1": "昨日海況", "lag2": "前日海況",
    "roll3": "近3日均況", "offshore": "外海比例", "month": "月份", "weekday": "星期",
}


def train_sea_classifier(att, output_dir=None) -> dict | None:
    """訓練 RandomForest 預測明日惡劣海況。回傳指標 + 特徵重要度 + 明日機率；可存 joblib。"""
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, roc_auc_score
    except Exception as e:
        print(f"[analysis] scikit-learn 未安裝，跳過海況預測模型：{e}")
        return None

    built = _build_supervised(att)
    if built is None:
        return None
    feat_cols, train, last_feat = built
    if train["target"].nunique() < 2 or len(train) < 20:
        return None

    X = train[feat_cols].values
    y = train["target"].astype(int).values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    clf = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
    clf.fit(Xtr, ytr)

    pred = clf.predict(Xte)
    acc = float(accuracy_score(yte, pred))
    try:
        auc = float(roc_auc_score(yte, clf.predict_proba(Xte)[:, 1]))
    except Exception:
        auc = float("nan")

    prob_tomorrow = None
    if not last_feat.empty:
        prob_tomorrow = float(clf.predict_proba(last_feat[feat_cols].values)[0, 1])

    importances = {feat_cols[i]: float(clf.feature_importances_[i]) for i in range(len(feat_cols))}

    if output_dir is not None:
        try:
            import joblib
            joblib.dump({"model": clf, "features": feat_cols},
                        Path(output_dir) / "sea_predictor.joblib")
            print("  ✔ sea_predictor.joblib")
        except Exception as e:
            print(f"[analysis] joblib 儲存跳過：{e}")

    return {
        "accuracy": round(acc, 3),
        "auc": round(auc, 3) if auc == auc else None,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "importances": importances,
        "prob_tomorrow": round(prob_tomorrow * 100, 1) if prob_tomorrow is not None else None,
    }


def _chart_feature_importance(att):
    """圖：海況預測模型特徵重要度（RandomForest）。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    res = train_sea_classifier(att)
    if res is None:
        ax.set_title("海況預測模型特徵重要度（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    imp = res["importances"]
    items = sorted(imp.items(), key=lambda kv: kv[1])
    names = [FEATURE_LABELS.get(k, k) for k, _ in items]
    vals  = [v for _, v in items]
    bars = ax.barh(names, vals, color=BLUE_PAL[2], edgecolor="white")
    ax.bar_label(bars, fmt="%.3f", padding=4, fontsize=9)
    auc_txt = f"，AUC = {res['auc']}" if res.get("auc") is not None else ""
    ax.set_title(f"明日惡劣海況預測：特徵重要度（RandomForest，準確率 {res['accuracy']}{auc_txt}）",
                 fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("特徵重要度（Gini importance）")
    fig.tight_layout(); return fig


# ════════════════════════════════════════════════════════════════════════════
#  人力資源與排班決策引擎（核心差異化）
#  ── 海象僅為輸入之一；輸出為「人員疲勞 / 工時公平 / 船艦可用 / 明日班表」決策。
# ════════════════════════════════════════════════════════════════════════════

# 船艦母港對應海域已於上方 VESSEL_ZONE 定義。
MAINT_INTERVAL = 45   # 每累計約 45 趟值勤需進廠維護一次（模擬維護門檻）


def _consecutive_days(dates) -> int:
    """計算「結束於最後一次值勤」的連續值勤天數。"""
    ds = sorted({d for d in dates})
    if not ds:
        return 0
    streak = 1
    for i in range(len(ds) - 1, 0, -1):
        if (ds[i] - ds[i - 1]).days == 1:
            streak += 1
        else:
            break
    return streak


def compute_fatigue(att) -> list:
    """人員疲勞指數：連續值勤天數 + 近 7 日工時 + 近期活躍度 → 0~100 分。"""
    if att is None or att.empty:
        return []
    ref = att["work_date"].max().normalize()
    out = []
    for uid, g in att.groupby("user_id"):
        name = g["full_name"].iloc[0]
        dates = [d.date() for d in g["work_date"]]
        consec = _consecutive_days(dates)
        last7 = g[g["work_date"] >= ref - pd.Timedelta(days=6)]
        h7 = float(last7["hours"].sum())
        last_duty = g["work_date"].max().normalize()
        days_since = int((ref - last_duty).days)
        # 以資料末日為「現在」：連續值勤天數為主，近 7 日工時為輔
        score = min(100, consec * 9 + h7 * 0.45)
        level = "high" if score >= 65 else "mid" if score >= 40 else "low"
        out.append({
            "user_id": int(uid), "name": name,
            "consecutive_days": int(consec),
            "hours_7d": round(h7, 1),
            "days_since_duty": days_since,
            "fatigue_score": int(round(score)),
            "level": level,
        })
    return sorted(out, key=lambda x: x["fatigue_score"], reverse=True)


def compute_fairness(att) -> dict:
    """工時公平性：Gini 係數 + 過勞 / 閒置人員辨識（基於累計工時偏離中位數）。"""
    if att is None or att.empty:
        return {}
    per = att.groupby(["user_id", "full_name"])["hours"].sum().reset_index()
    if len(per) < 3:
        return {}
    vals = np.sort(per["hours"].values)
    n = len(vals); idx = np.arange(1, n + 1)
    gini = float((2 * (idx * vals).sum() - (n + 1) * vals.sum()) / (n * vals.sum())) if vals.sum() else 0.0
    median = float(per["hours"].median())
    over = per[per["hours"] >= median * 1.3].sort_values("hours", ascending=False)
    under = per[per["hours"] <= median * 0.7].sort_values("hours")
    fair_label = "均勻" if gini < 0.2 else "尚可" if gini < 0.35 else "失衡"
    return {
        "gini": round(gini, 3),
        "label": fair_label,
        "median_hours": round(median, 1),
        "overworked": [{"name": r["full_name"], "hours": round(float(r["hours"]), 1)}
                       for _, r in over.head(3).iterrows()],
        "underused": [{"name": r["full_name"], "hours": round(float(r["hours"]), 1)}
                      for _, r in under.head(3).iterrows()],
        # Lorenz 曲線座標供繪圖
        "lorenz": {
            "x": [round(i / n, 3) for i in range(n + 1)],
            "y": [0.0] + [round(float(v), 3) for v in (np.cumsum(vals) / vals.sum())] if vals.sum() else [0.0] * (n + 1),
        },
    }


def compute_vessel_status(att) -> list:
    """船艦可用性與維護：累計趟次 → 維護里程，輸出可用 / 需維護狀態。"""
    if att is None or att.empty:
        return []
    out = []
    for v, g in att.groupby("vessel_id"):
        total = int(len(g))
        since = total % MAINT_INTERVAL
        due = since >= MAINT_INTERVAL * 0.85
        last_used = g["work_date"].max().date()
        out.append({
            "vessel": str(v), "zone": VESSEL_ZONE.get(str(v), "近海"),
            "total_duties": total,
            "since_maint": int(since),
            "maint_interval": MAINT_INTERVAL,
            "availability_pct": int(round(100 * (1 - since / MAINT_INTERVAL))),
            "status": "需維護" if due else "可用",
            "last_used": str(last_used),
        })
    return sorted(out, key=lambda x: x["vessel"])


def build_schedule(att, fatigue, vessel_status, exposure_ranking,
                   rough_prob: float) -> dict:
    """
    自動排班引擎：依「明日惡劣海況機率 + 人員疲勞 + 外海暴露 + 船艦可用性」
    產生明日值勤班表（誰上哪艦、哪海域）。純海象資料無法生成此輸出。
    """
    # 排班「現在」基準採資料末日，使班表與疲勞 / 暴露口徑一致
    if att is not None and not att.empty:
        tomorrow = (att["work_date"].max().normalize() + pd.Timedelta(days=1)).date()
    else:
        tomorrow = (pd.Timestamp.today().normalize() + pd.Timedelta(days=1)).date()

    # 班表需求：惡劣海況 → 縮減外海員額
    if rough_prob >= 50:
        zone_slots = {"港口": 3, "近海": 3, "外海": 1}
    elif rough_prob >= 25:
        zone_slots = {"港口": 2, "近海": 3, "外海": 2}
    else:
        zone_slots = {"港口": 2, "近海": 3, "外海": 3}
    total_slots = sum(zone_slots.values())

    fatigue_map = {f["user_id"]: f for f in fatigue}
    expo_map = {e["user_id"]: e for e in exposure_ranking}

    # 候選人池（近期活躍人員）
    cands = []
    for uid, f in fatigue_map.items():
        offshore_pct = expo_map.get(uid, {}).get("offshore_pct", 0.0)
        cands.append({
            "user_id": uid, "name": f["name"],
            "fatigue_score": f["fatigue_score"], "level": f["level"],
            "offshore_pct": offshore_pct,
        })

    # 高疲勞者建議休息：依疲勞由高到低，但保留足夠人力填滿班表
    rest_cap = max(0, len(cands) - total_slots)
    high_fat = sorted([c for c in cands if c["fatigue_score"] >= 75],
                      key=lambda c: c["fatigue_score"], reverse=True)
    rest = high_fat[:rest_cap]
    rest_ids = {c["user_id"] for c in rest}
    pool = [c for c in cands if c["user_id"] not in rest_ids]

    # 可用船艦（排除需維護），依海域分組
    avail_by_zone = {z: [] for z in DUTY_ZONES}
    for v in vessel_status:
        if v["status"] == "可用":
            avail_by_zone.setdefault(v["zone"], []).append(v["vessel"])

    schedule = []
    assigned = set()
    vessel_limited = []   # 因可用船艦不足而無法排滿員額的海域
    # 由外海→近海→港口指派；外海優先給「低疲勞 + 低外海暴露」者（安全 + 公平輪換）
    for zone in ["外海", "近海", "港口"]:
        n = zone_slots.get(zone, 0)
        if zone == "外海":
            ranked = sorted(pool, key=lambda c: c["fatigue_score"] * 0.6 + c["offshore_pct"] * 0.4)
        elif zone == "近海":
            ranked = sorted(pool, key=lambda c: c["fatigue_score"])
        else:  # 港口：留給疲勞較高者（輕負荷）
            ranked = sorted(pool, key=lambda c: -c["fatigue_score"])
        # 每艘可用船艦僅配一組人員（避免同艦重複指派）；員額受可用艦數上限約束
        vessels = list(avail_by_zone.get(zone, []))
        effective_n = min(n, len(vessels)) if vessels else 0
        if effective_n < n:
            vessel_limited.append({"zone": zone, "slots": n, "filled": effective_n,
                                   "available_vessels": len(vessels)})
        vi = 0
        for c in ranked:
            if vi >= effective_n:
                break
            if c["user_id"] in assigned:
                continue
            vessel = vessels[vi]; vi += 1
            if zone == "外海":
                reason = "低疲勞且外海暴露低，適合輪派外海"
            elif zone == "近海":
                reason = "疲勞適中，配置近海任務"
            else:
                reason = "疲勞偏高，配置港口輕負荷" if c["fatigue_score"] >= 40 else "配置港口值守"
            schedule.append({
                "name": c["name"], "zone": zone, "vessel": vessel,
                "fatigue_score": c["fatigue_score"], "offshore_pct": c["offshore_pct"],
                "reason": reason,
            })
            assigned.add(c["user_id"])

    maint_vessels = [v["vessel"] for v in vessel_status if v["status"] == "需維護"]
    return {
        "date": str(tomorrow),
        "rough_prob": round(float(rough_prob), 1),
        "zone_slots": zone_slots,
        "assignments": schedule,
        "rest_recommended": [{"name": c["name"], "fatigue_score": c["fatigue_score"]} for c in rest],
        "maintenance_vessels": maint_vessels,
        "vessel_limited": vessel_limited,
    }


def _chart_fatigue(att):
    """圖：人員疲勞指數排行（連續值勤 + 近 7 日工時）。"""
    fig, ax = plt.subplots(figsize=(8.5, 5))
    fat = compute_fatigue(att)
    if not fat:
        ax.set_title("人員疲勞指數（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    fat = sorted(fat, key=lambda x: x["fatigue_score"])
    names = [f["name"] for f in fat]
    scores = [f["fatigue_score"] for f in fat]
    colors = ["#c0001e" if s >= 60 else "#ef6c00" if s >= 35 else BLUE_PAL[3] for s in scores]
    bars = ax.barh(names, scores, color=colors, edgecolor="white")
    ax.bar_label(bars, padding=4, fontsize=9)
    ax.axvline(60, color="#c0001e", ls="--", lw=1, alpha=0.6)
    ax.axvline(35, color="#ef6c00", ls="--", lw=1, alpha=0.5)
    ax.set_xlim(0, 105)
    ax.set_title("人員疲勞指數排行（紅=高疲勞 ≥60）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("疲勞分數（0~100）")
    fig.tight_layout(); return fig


def _chart_fairness_lorenz(att):
    """圖：工時公平性 Lorenz 曲線（對角線 = 完全平均）。"""
    fig, ax = plt.subplots(figsize=(7, 6))
    fr = compute_fairness(att)
    if not fr or "lorenz" not in fr:
        ax.set_title("工時公平性 Lorenz 曲線（資料不足）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    x = fr["lorenz"]["x"]; y = fr["lorenz"]["y"]
    ax.plot([0, 1], [0, 1], color="#888", ls="--", lw=1.3, label="完全平均")
    ax.plot(x, y, color=BLUE_PAL[2], lw=2.4, marker="o", markersize=4, label="實際工時分布")
    ax.fill_between(x, y, x, color=BLUE_PAL[2], alpha=0.12)
    ax.set_title(f"工時公平性 Lorenz 曲線（Gini = {fr['gini']}，{fr['label']}）",
                 fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("人員累計比例"); ax.set_ylabel("工時累計比例")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.tight_layout(); return fig


def _chart_vessel_availability(att):
    """圖：船艦可用性與維護里程。"""
    fig, ax = plt.subplots(figsize=(9, 5))
    vs = compute_vessel_status(att)
    if not vs:
        ax.set_title("船艦可用性（無資料）", fontsize=14, fontweight="bold")
        fig.tight_layout(); return fig
    vs = sorted(vs, key=lambda x: x["availability_pct"])
    names = [v["vessel"] for v in vs]
    avail = [v["availability_pct"] for v in vs]
    colors = ["#c0001e" if v["status"] == "需維護" else BLUE_PAL[2] for v in vs]
    bars = ax.barh(names, avail, color=colors, edgecolor="white")
    ax.bar_label(bars, fmt="%d%%", padding=4, fontsize=9)
    ax.axvline(15, color="#c0001e", ls="--", lw=1, alpha=0.6, label="維護門檻")
    ax.set_xlim(0, 105)
    ax.set_title("船艦可用性（距下次維護里程，紅=需維護）", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("可用度 (%)")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout(); return fig


# ── 統計檢定報告 ─────────────────────────────────────────────────────────────
def compute_stats(att, leaves) -> dict:
    """
    跑 ANOVA、卡方獨立性檢定、Pareto 80/20、Gini，回傳結構化結果。
    供 PHP 儀表板用 JSON 形式呈現。
    """
    out = {"generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
           "summary": {}, "tests": [], "insights": []}

    if att.empty:
        out["summary"]["error"] = "無有效值勤資料"
        return out

    # ── 基本摘要 ──
    out["summary"]["records"]      = int(len(att))
    out["summary"]["people"]       = int(att["user_id"].nunique())
    out["summary"]["vessels"]      = int(att["vessel_id"].nunique())
    out["summary"]["date_range"]   = f"{att['work_date'].min().date()} ～ {att['work_date'].max().date()}"
    out["summary"]["hours_mean"]   = round(float(att["hours"].mean()), 2)
    out["summary"]["hours_median"] = round(float(att["hours"].median()), 2)
    out["summary"]["hours_std"]    = round(float(att["hours"].std()), 2)

    # ── 檢定 1：海況是否影響工時（單因子 ANOVA）──
    sea_groups = [g["hours"].values for _, g in att.groupby("sea_state") if len(g) >= 3]
    if len(sea_groups) >= 2:
        f, p = sps.f_oneway(*sea_groups)
        out["tests"].append({
            "name": "海況對工時的影響（單因子 ANOVA）",
            "h0": "各海況下的平均工時相同",
            "statistic": f"F = {f:.3f}",
            "p_value": float(p),
            "p_display": f"{p:.4f}" if p >= 0.0001 else "< 0.0001",
            "significant": bool(p < 0.05),
            "conclusion": "拒絕 H0：海況顯著影響工時" if p < 0.05 else "未達顯著水準，無法證明海況影響工時",
        })

    # ── 檢定 2：海域與海況是否獨立（卡方獨立性）──
    cross = pd.crosstab(att["duty_zone"], att["sea_state"])
    if cross.shape[0] >= 2 and cross.shape[1] >= 2:
        chi2, p, dof, _ = sps.chi2_contingency(cross)
        out["tests"].append({
            "name": "海域與海況的獨立性（卡方檢定）",
            "h0": "海域與海況彼此獨立（隨機分布）",
            "statistic": f"χ² = {chi2:.3f}, df = {dof}",
            "p_value": float(p),
            "p_display": f"{p:.4f}" if p >= 0.0001 else "< 0.0001",
            "significant": bool(p < 0.05),
            "conclusion": "拒絕 H0：海域分布與海況有顯著關聯" if p < 0.05 else "未達顯著水準，可視為獨立",
        })

    # ── 洞察 1：Pareto 80/20 ──
    counts = att["vessel_id"].value_counts().sort_values(ascending=False)
    if len(counts) > 0:
        cum = counts.cumsum() / counts.sum()
        n_for_80 = int((cum <= 0.8).sum() + 1)
        pct_vessel = round(n_for_80 / len(counts) * 100, 1)
        out["insights"].append({
            "title": "Pareto 80/20 法則檢視",
            "text": f"承擔前 80% 工作量需 {n_for_80} / {len(counts)} 艘船艦（{pct_vessel}%）。"
                    f"{'符合' if pct_vessel <= 30 else '不符合'} Pareto 集中度（≤ 30% 為集中）。"
        })

    # ── 洞察 2：人員工作分配 Gini 係數 ──
    person_hours = att.groupby("user_id")["hours"].sum().values
    if len(person_hours) >= 3:
        sorted_h = np.sort(person_hours)
        n = len(sorted_h); idx = np.arange(1, n + 1)
        gini = (2 * (idx * sorted_h).sum() - (n + 1) * sorted_h.sum()) / (n * sorted_h.sum())
        out["insights"].append({
            "title": "人員工時分配公平性（Gini 係數）",
            "text": f"Gini = {gini:.3f}（0 = 完全平均、1 = 極度集中）。"
                    f"{'分配相當均勻' if gini < 0.2 else '分配尚算合理' if gini < 0.35 else '分配明顯不均，建議重新調度'}。"
        })

    # ── 洞察 3：異常值勤 ──
    if len(att) >= 10:
        z = np.abs(sps.zscore(att["hours"]))
        n_outlier = int((z > 2).sum())
        out["insights"].append({
            "title": "異常工時檢測",
            "text": f"共 {n_outlier} 筆值勤之工時偏離平均 2 個標準差以上（占 {n_outlier/len(att)*100:.1f}%）。"
                    f"{'建議覆核這些紀錄' if n_outlier > 0 else '所有紀錄都在正常範圍內'}。"
        })

    # ── 洞察 4：請假狀況 ──
    if not leaves.empty:
        approved = leaves[leaves["status"] == "approved"]
        pending  = leaves[leaves["status"] == "pending"]
        out["insights"].append({
            "title": "請假狀態總覽",
            "text": f"共 {len(leaves)} 件請假申請，已核准 {len(approved)} 件、待審 {len(pending)} 件。"
                    f"{'有待審件，建議盡快處理' if len(pending) > 0 else '無待審件'}。"
        })

    # ── 洞察 5：工時驅動因子（多元線性迴歸建模）──
    ols = _fit_hours_ols(att)
    if ols is not None:
        r2, coefs = ols
        top = max(coefs, key=lambda k: abs(coefs[k]))
        direction = "拉長" if coefs[top] > 0 else "縮短"
        out["insights"].append({
            "title": "工時驅動因子（多元線性迴歸 OLS）",
            "text": f"以海況、海域、星期、上工時刻四項特徵建模，R² = {r2:.3f}，"
                    f"可解釋約 {r2 * 100:.0f}% 的單次工時變異。影響最大的因子為「{top}」"
                    f"（標準化係數 {coefs[top]:+.3f}，{direction}工時）。"
        })
        out["model"] = {"r2": round(float(r2), 3),
                        "coefficients": {k: round(float(v), 3) for k, v in coefs.items()}}

    # ── 洞察 6：未來值勤量預測（週線性外推）──
    if att["work_date"].nunique() >= 14:
        weekly = att.set_index("work_date").resample("W")["att_id"].count()
        weekly = weekly[weekly > 0]
        _today = pd.Timestamp.today().normalize()
        if len(weekly) >= 2 and weekly.index[-1].normalize() > _today:
            weekly = weekly.iloc[:-1]
        if len(weekly) >= 6:
            yv = weekly.values.astype(float)
            slope, intercept = np.polyfit(np.arange(len(yv)), yv, 1)
            nxt = slope * len(yv) + intercept
            trend_txt = "上升" if slope > 0.3 else "下降" if slope < -0.3 else "大致持平"
            out["insights"].append({
                "title": "未來值勤量預測（線性趨勢外推）",
                "text": f"近 {len(weekly)} 週的值勤量趨勢{trend_txt}"
                        f"（每週約 {slope:+.1f} 筆）。依線性外推，下一週預估約 {max(nxt, 0):.0f} 筆。"
            })

    return out


# ── 勤務決策建議 ──────────────────────────────────────────────────────────────
def compute_recommendations(att, sea_obs=None, output_dir=None) -> dict:
    """
    以近 30 天值勤資料計算海象感知排班決策建議。
    回傳 dict 供 PHP 儀表板呈現（存成 recommendations.json）。
    sea_obs：即時海況觀測（sea_observations）；output_dir：供 ML 模型 joblib 落地。
    """
    out = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "headline": "",
        "zone_risk": [],
        "exposure_ranking": [],
        "alerts": [],
        "rotation_suggestions": [],
        "markov_rough_7day": None,
        "ml_rough_tomorrow": None,
        "ml_metrics": None,
        "sea_now": latest_sea_now(sea_obs),
        "fatigue": [],
        "fairness": {},
        "vessel_status": [],
        "schedule": {},
    }

    if att.empty:
        out["headline"] = "目前無有效值勤資料，無法產生建議"
        return out

    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=30)
    recent = att[att["work_date"] >= cutoff]
    if len(recent) < 5:
        recent = att

    # 各海域近況
    zone_stats = []
    for zone in DUTY_ZONES:
        zd = recent[recent["duty_zone"] == zone]
        if len(zd) == 0:
            continue
        rough_pct = float((zd["sea_state"] == "大浪").mean() * 100)
        zone_stats.append({
            "zone": zone,
            "count": int(len(zd)),
            "avg_sea_rank": round(float(zd["sea_state"].map(SEA_RANK).mean()), 2),
            "avg_hours": round(float(zd["hours"].mean()), 2),
            "rough_pct": round(rough_pct, 1),
        })
    out["zone_risk"] = sorted(zone_stats, key=lambda x: x["avg_sea_rank"], reverse=True)

    # 人員外海暴露排名
    per_person = []
    for uid, g in recent.groupby("user_id"):
        per_person.append({
            "user_id": int(uid),
            "records": int(len(g)),
            "offshore_pct": round(float((g["duty_zone"] == "外海").mean() * 100), 1),
            "rough_sea_pct": round(float((g["sea_state"] == "大浪").mean() * 100), 1),
            "avg_hours": round(float(g["hours"].mean()), 2),
        })
    out["exposure_ranking"] = sorted(per_person, key=lambda x: x["offshore_pct"], reverse=True)

    # 警示
    alerts = []
    rough_overall = float((recent["sea_state"] == "大浪").mean())
    if rough_overall > 0.2:
        alerts.append({
            "level": "warn",
            "text": f"近 30 天大浪比例 {rough_overall*100:.0f}%，超過安全閾值 20%，建議縮減外海任務。",
        })
    danger = recent[(recent["duty_zone"] == "外海") & (recent["sea_state"] == "大浪")]
    if len(danger) > 0:
        pct = len(danger) / len(recent) * 100
        alerts.append({
            "level": "err" if pct >= 10 else "warn",
            "text": f"外海 × 大浪值勤共 {len(danger)} 筆（占 {pct:.1f}%），請評估人員安全風險。",
        })
    long_duty = recent[recent["hours"] > 12]
    if len(long_duty) > 0:
        alerts.append({
            "level": "info",
            "text": f"近期有 {len(long_duty)} 筆值勤超過 12 小時，請確認人員是否充分休息。",
        })
    # Markov 7 天大浪期望機率預警
    if len(att) >= 10:
        trans = _compute_markov_transition(att)
        last_valid = att.sort_values("work_date")["sea_state"].dropna()
        if not last_valid.empty:
            last_idx = SEA_STATES.index(last_valid.iloc[-1])
            probs = np.zeros((8, len(SEA_STATES)))
            probs[0, last_idx] = 1.0
            for _d in range(1, 8):
                probs[_d] = probs[_d - 1] @ trans
            rough_7day = float(probs[1:, SEA_STATES.index("大浪")].mean())
            out["markov_rough_7day"] = round(rough_7day * 100, 1)
            if rough_7day > 0.15:
                alerts.append({
                    "level": "warn",
                    "text": (
                        f"Markov 預測：未來 7 天大浪期望機率 {rough_7day*100:.0f}%，"
                        "建議提前評估外海任務是否需調整排班。"
                    ),
                })

    # scikit-learn 模型：預測明日是否惡劣海況（中浪以上）
    ml = train_sea_classifier(att, output_dir=output_dir)
    if ml is not None:
        out["ml_rough_tomorrow"] = ml.get("prob_tomorrow")
        out["ml_metrics"] = {"accuracy": ml.get("accuracy"), "auc": ml.get("auc"),
                             "n_train": ml.get("n_train"), "n_test": ml.get("n_test")}
        ptm = ml.get("prob_tomorrow")
        if ptm is not None and ptm > 50:
            alerts.append({
                "level": "warn",
                "text": (
                    f"機器學習模型（RandomForest，準確率 {ml.get('accuracy')}）預測："
                    f"明日惡劣海況機率 {ptm}%，建議審視明日外海排班。"
                ),
            })

    if not alerts:
        alerts.append({
            "level": "ok",
            "text": "近期海況與值勤負荷均在正常範圍內，目前無異常警示。",
        })
    out["alerts"] = alerts

    # 輪換建議：以相對排名產生具名調度指令
    # 將風險積分 (外海比例×0.6 + 大浪比例×0.4) 排序，取前 3 高暴露者建議輪換
    ranked = sorted(
        out["exposure_ranking"],
        key=lambda x: x["offshore_pct"] * 0.6 + x["rough_sea_pct"] * 0.4,
        reverse=True,
    )
    avg_offshore = float(np.mean([p["offshore_pct"] for p in ranked])) if ranked else 0
    suggestions = []
    for p in ranked:
        uid = p["user_id"]
        name_col = recent[recent["user_id"] == uid]["full_name"]
        name = name_col.iloc[0] if len(name_col) > 0 else f"UID {uid}"
        score = p["offshore_pct"] * 0.6 + p["rough_sea_pct"] * 0.4
        avg_score = avg_offshore * 0.6
        # 高暴露：絕對超過 50%，或相對高於平均 1.5 倍且排前 3
        if p["offshore_pct"] >= 50 or (score > avg_score * 1.5 and len(suggestions) < 3):
            suggestions.append({
                "name": name,
                "offshore_pct": p["offshore_pct"],
                "rough_sea_pct": p["rough_sea_pct"],
                "action": "建議下週調至港口值勤（外海暴露偏高）",
                "priority": "high",
            })
        # 低暴露：排名後段、外海比例低於平均一半，最多列 2 人作為接替候選
        elif p["offshore_pct"] < avg_offshore * 0.5 and len([s for s in suggestions if s["priority"] == "normal"]) < 2:
            suggestions.append({
                "name": name,
                "offshore_pct": p["offshore_pct"],
                "rough_sea_pct": p["rough_sea_pct"],
                "action": "外海暴露率低，可接替外海勤務",
                "priority": "normal",
            })
    out["rotation_suggestions"] = suggestions

    # ── 人力資源與排班決策引擎（核心差異化）──────────────────────────────────
    # 疲勞 / 公平性 / 船艦可用性 以全期資料計算（趨勢需足夠樣本），班表以此為輸入。
    out["fatigue"] = compute_fatigue(att)
    out["fairness"] = compute_fairness(att)
    out["vessel_status"] = compute_vessel_status(att)

    # 明日惡劣海況機率：優先採 ML，其次 Markov，再退回近期大浪比例
    rough_prob = out.get("ml_rough_tomorrow")
    if rough_prob is None:
        rough_prob = out.get("markov_rough_7day")
    if rough_prob is None:
        rough_prob = round(rough_overall * 100, 1)
    out["schedule"] = build_schedule(
        att, out["fatigue"], out["vessel_status"],
        out["exposure_ranking"], float(rough_prob),
    )

    # 疲勞 / 維護警示
    high_fat = [f for f in out["fatigue"] if f["level"] == "high"]
    if high_fat:
        names = "、".join(f["name"] for f in high_fat[:3])
        alerts.append({
            "level": "warn",
            "text": f"疲勞偵測：{names} 等 {len(high_fat)} 人疲勞指數偏高（連續值勤過長），建議安排輪休。",
        })
    maint = [v for v in out["vessel_status"] if v["status"] == "需維護"]
    if maint:
        alerts.append({
            "level": "info",
            "text": f"船艦維護：{('、'.join(v['vessel'] for v in maint))} 已達維護里程，明日排班已自動排除。",
        })
    out["alerts"] = alerts

    # 標題
    worst_zone = max(zone_stats, key=lambda x: x["rough_pct"]) if zone_stats else None
    if worst_zone and worst_zone["rough_pct"] > 15:
        out["headline"] = (
            f"近 30 天「{worst_zone['zone']}」大浪比例最高（{worst_zone['rough_pct']}%），"
            "建議優先評估值勤調度。"
        )
    elif len(alerts) > 1 or (alerts and alerts[0]["level"] in ("warn", "err")):
        out["headline"] = "系統偵測到近期值勤風險，請參閱下方警示。"
    else:
        out["headline"] = "近期海況平穩，各海域值勤運作正常。"

    return out


# ── 圖 12：模擬 vs 觀測海況對照（需先執行 fetch_sea_data.py）────────────────────
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
    except Exception as e:
        print(f"[analysis] sea_obs_comparison skipped: {e}")
        return None

    if obs.empty:
        return None

    sea_order = SEA_STATES

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
    att, leaves = _load_data(conn, None, None)
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
