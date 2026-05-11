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


# ── 圖 8：海域 × 海況 平均工時熱力圖 ─────────────────────────────────────────
def _chart_hours_heatmap(att):
    """揭露兩個維度的交互效應：同樣海況下，不同海域工時差多少？"""
    sea_order  = [s for s in ["平靜", "輕浪", "中浪", "大浪"] if s in att["sea_state"].values]
    zone_order = [z for z in ["港口", "近海", "外海"] if z in att["duty_zone"].values]
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
