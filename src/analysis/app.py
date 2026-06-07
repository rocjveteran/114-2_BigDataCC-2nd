#!/usr/bin/env python3
"""
Gradio 互動分析介面 — 視覺風格對齊 PHP 系統的編輯感主題。
"""

import json
import os
from pathlib import Path
from datetime import date

import gradio as gr
from analysis import generate_charts, compute_recommendations, get_connection, get_filter_options

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))

CHART_TABS = [
    {
        "label": "時序趨勢",
        "charts": [
            ("monthly_trend.png",   "月度值勤人次趨勢"),
            ("leave_trend.png",     "每月核准請假件數"),
            ("weekday_pattern.png", "週幾出勤模式"),
        ],
    },
    {
        "label": "預測與建模",
        "charts": [
            ("forecast_duty.png",      "值勤量時間序列預測"),
            ("correlation_matrix.png", "特徵相關矩陣（Spearman）"),
            ("regression_coef.png",    "工時驅動因子（OLS 迴歸）"),
            ("crew_clusters.png",      "人員值勤模式分群（K-means）"),
            ("markov_heatmap.png",     "海況 Markov 轉移矩陣 + 7 天預測"),
            ("feature_importance.png", "海況預測特徵重要度（RandomForest）"),
        ],
    },
    {
        "label": "人力資源決策",
        "charts": [
            ("fatigue.png",             "人員疲勞指數排行"),
            ("fairness_lorenz.png",     "工時公平性 Lorenz 曲線"),
            ("vessel_availability.png", "船艦可用性與維護里程"),
            ("zone_map_static.png",     "海域配置示意圖"),
        ],
    },
    {
        "label": "海域 × 海況",
        "charts": [
            ("zone_bar.png",         "值勤海域分布"),
            ("zone_sea_stacked.png", "各海域海況分布"),
            ("hours_boxplot.png",    "各海況值勤時數分布"),
            ("hours_heatmap.png",    "海域×海況平均工時"),
        ],
    },
    {
        "label": "資源調度",
        "charts": [
            ("vessel_count.png",  "各船艦值勤次數"),
            ("vessel_pareto.png", "船艦使用 Pareto 圖"),
            ("person_heatmap.png","人員月度出勤熱力圖"),
        ],
    },
    {
        "label": "異常診斷",
        "charts": [
            ("anomaly_detect.png", "異常值勤偵測（Z-score）"),
        ],
    },
]

CHART_LABELS = [c[1] for tab in CHART_TABS for c in tab["charts"]]
CHART_FILES  = [c[0] for tab in CHART_TABS for c in tab["charts"]]

ZONE_OPTIONS = ["港口", "近海", "外海"]


def _load_options():
    try:
        conn = get_connection()
        opts = get_filter_options(conn)
        conn.close()
        return opts
    except Exception:
        return {"vessels": [], "zones": ZONE_OPTIONS,
                "date_min": date(2025, 11, 1), "date_max": date(2026, 4, 30)}


# ── 主題 ──────────────────────────────────────────────────────────────────────
maritime_theme = gr.themes.Base(
    primary_hue=gr.themes.Color(
        c50="#fdf2ec", c100="#fbdfd2", c200="#f5b89e", c300="#ec926e",
        c400="#df7b56", c500="#c96442", c600="#b5502f", c700="#9a4126",
        c800="#7d3520", c900="#5f281a", c950="#3e1a11",
    ),
    neutral_hue=gr.themes.Color(
        c50="#faf9f5", c100="#f5f4ef", c200="#ece9e1", c300="#e3dfd5",
        c400="#c8c2b3", c500="#9a948a", c600="#6b6862", c700="#4a4843",
        c800="#36352f", c900="#141413", c950="#0a0a09",
    ),
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
).set(
    # 亮色 & 暗色都用同一組顏色，停用 dark-mode 自動切換
    body_background_fill="#faf9f5",
    body_background_fill_dark="#faf9f5",
    body_text_color="#141413",
    body_text_color_dark="#141413",
    background_fill_primary="#ffffff",
    background_fill_primary_dark="#ffffff",
    background_fill_secondary="#faf9f5",
    background_fill_secondary_dark="#faf9f5",
    border_color_primary="#e8e5dc",
    border_color_primary_dark="#e8e5dc",
    border_color_accent="#c96442",
    border_color_accent_dark="#c96442",
    button_primary_background_fill="#c96442",
    button_primary_background_fill_dark="#c96442",
    button_primary_background_fill_hover="#b5502f",
    button_primary_background_fill_hover_dark="#b5502f",
    button_primary_text_color="#ffffff",
    button_primary_text_color_dark="#ffffff",
    button_primary_border_color="*primary_500",
    button_primary_border_color_dark="*primary_500",
    button_secondary_background_fill="#ffffff",
    button_secondary_background_fill_dark="#ffffff",
    button_secondary_background_fill_hover="#f1efe7",
    button_secondary_background_fill_hover_dark="#f1efe7",
    button_secondary_text_color="#141413",
    button_secondary_text_color_dark="#141413",
    button_secondary_border_color="#e8e5dc",
    button_secondary_border_color_dark="#e8e5dc",
    block_background_fill="#ffffff",
    block_background_fill_dark="#ffffff",
    block_border_color="#e8e5dc",
    block_border_color_dark="#e8e5dc",
    block_border_width="1px",
    block_radius="10px",
    block_shadow="none",
    block_shadow_dark="none",
    block_label_text_color="#6b6862",
    block_label_text_color_dark="#6b6862",
    block_label_background_fill="#ffffff",
    block_label_background_fill_dark="#ffffff",
    block_label_text_weight="500",
    block_label_text_size="13px",
    block_title_text_color="#141413",
    block_title_text_color_dark="#141413",
    block_title_text_weight="500",
    input_background_fill="#ffffff",
    input_background_fill_dark="#ffffff",
    input_background_fill_focus="#ffffff",
    input_background_fill_focus_dark="#ffffff",
    input_border_color="#e8e5dc",
    input_border_color_dark="#e8e5dc",
    input_border_color_focus="#c96442",
    input_border_color_focus_dark="#c96442",
    input_shadow_focus="0 0 0 3px rgba(201,100,66,0.1)",
    input_shadow_focus_dark="0 0 0 3px rgba(201,100,66,0.1)",
    panel_background_fill="#ffffff",
    panel_background_fill_dark="#ffffff",
    panel_border_color="#e8e5dc",
    panel_border_color_dark="#e8e5dc",
    color_accent_soft="rgba(201,100,66,0.08)",
    color_accent_soft_dark="rgba(201,100,66,0.08)",
    checkbox_background_color="#ffffff",
    checkbox_background_color_dark="#ffffff",
    checkbox_background_color_selected="#c96442",
    checkbox_background_color_selected_dark="#c96442",
    checkbox_border_color="#e8e5dc",
    checkbox_border_color_dark="#e8e5dc",
    checkbox_label_background_fill="#ffffff",
    checkbox_label_background_fill_dark="#ffffff",
    checkbox_label_background_fill_hover="#f1efe7",
    checkbox_label_background_fill_hover_dark="#f1efe7",
    checkbox_label_text_color="#141413",
    checkbox_label_text_color_dark="#141413",
)


# ── 自訂 CSS ──────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500&family=Inter:wght@400;500;600&family=Noto+Serif+TC:wght@400;500&display=swap');

/* 強制亮色：覆蓋系統 dark mode preference（精準覆蓋、不動 checkbox/dropdown 狀態） */
html, body { color-scheme: light !important; }
html.dark, body.dark, .dark { background: #faf9f5 !important; color: #141413 !important; }
.dark .gradio-container { background: #faf9f5 !important; color: #141413 !important; }
.dark .block, .dark .form, .dark .gr-form, .dark .gr-box, .dark .gr-panel { background: #ffffff !important; border-color: #e8e5dc !important; }
.dark label, .dark .label-wrap span, .dark .block label span { color: #36352f !important; }
.dark input[type="text"], .dark input[type="number"], .dark input[type="date"], .dark textarea {
  background: #ffffff !important; color: #141413 !important; border-color: #e8e5dc !important;
}
.dark .gr-button-primary, .dark button.primary { background: #c96442 !important; color: #ffffff !important; border-color: #c96442 !important; }
.dark .gr-check-radio input[type="checkbox"]:checked,
.dark input[type="checkbox"]:checked { accent-color: #c96442 !important; }

.gradio-container {
  max-width: 1280px !important;
  margin: 0 auto !important;
  padding: 0 24px !important;
  background: #faf9f5 !important;
}

/* 隱藏 Gradio 預設 footer */
footer { display: none !important; }

/* ── Page hero ── */
.page-hero {
  padding: 48px 0 32px;
  border-bottom: 1px solid #e8e5dc;
  margin-bottom: 36px;
}
.page-hero .eyebrow {
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: #c96442;
  margin-bottom: 16px;
}
.page-hero h1 {
  font-family: "Source Serif 4", "Noto Serif TC", Georgia, serif !important;
  font-size: 46px !important;
  font-weight: 400 !important;
  letter-spacing: -0.9px !important;
  line-height: 1.1 !important;
  margin: 0 0 18px !important;
  color: #141413 !important;
}
.page-hero p.lead {
  font-size: 17px !important;
  line-height: 1.55 !important;
  color: #36352f !important;
  max-width: 720px !important;
  margin: 0 !important;
}

/* ── Section 小標 ── */
.section-eyebrow {
  font-size: 12px !important;
  font-weight: 600 !important;
  letter-spacing: 1px !important;
  text-transform: uppercase !important;
  color: #c96442 !important;
  margin: 8px 0 6px !important;
}
.section-eyebrow + h3,
.section-eyebrow ~ p {
  font-family: "Source Serif 4", "Noto Serif TC", Georgia, serif !important;
  font-size: 22px !important;
  font-weight: 400 !important;
  letter-spacing: -0.3px !important;
  color: #141413 !important;
  margin: 0 0 14px !important;
}

/* ── 篩選欄位卡片 ── */
.filter-panel,
.filter-panel > div,
.filter-panel .form,
.filter-panel .gr-form {
  background: #ffffff !important;
  border-color: #e8e5dc !important;
}
.filter-panel {
  border: 1px solid #e8e5dc !important;
  border-radius: 10px !important;
  padding: 20px !important;
  box-shadow: none !important;
}
.filter-panel > div { border: none !important; padding: 0 !important; }

/* ── Labels ── */
label > span.svelte-1gfkn6j,
label > span,
.gr-input-label {
  font-size: 13px !important;
  font-weight: 500 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  color: #36352f !important;
}

/* ── Inputs ── */
input[type="text"],
input[type="number"],
textarea,
.gr-textbox input,
.gr-textbox textarea {
  font-family: Inter, system-ui, sans-serif !important;
  font-size: 14.5px !important;
  border-radius: 7px !important;
  padding: 10px 13px !important;
  border: 1px solid #e8e5dc !important;
}
input:focus, textarea:focus { border-color: #c96442 !important; }

/* ── Primary button (執行分析) ── */
.gr-button-primary,
button.primary,
.lg button {
  background: #c96442 !important;
  border: 1px solid #c96442 !important;
  color: #fff !important;
  font-weight: 500 !important;
  letter-spacing: -0.1px !important;
  border-radius: 8px !important;
  padding: 12px 20px !important;
  box-shadow: none !important;
  transition: background .15s ease !important;
}
.gr-button-primary:hover,
button.primary:hover,
.lg button:hover { background: #b5502f !important; }

/* ── Status box ── */
.status-box textarea {
  background: #faf9f5 !important;
  border: 1px solid #e8e5dc !important;
  color: #141413 !important;
  font-weight: 500 !important;
}

/* ── 圖卡 ── */
.chart-image {
  background: #ffffff !important;
  border: 1px solid #e8e5dc !important;
  border-radius: 10px !important;
  padding: 14px !important;
  transition: border-color .15s ease;
}
.chart-image:hover { border-color: #d2cec1 !important; }
.chart-image label > span {
  font-family: "Source Serif 4", "Noto Serif TC", Georgia, serif !important;
  font-size: 15.5px !important;
  font-weight: 500 !important;
  color: #141413 !important;
  letter-spacing: -0.1px !important;
  margin-bottom: 8px !important;
}

/* ── Page footer ── */
.page-footer {
  margin-top: 64px;
  padding: 24px 0;
  border-top: 1px solid #e8e5dc;
  color: #6b6862;
  font-size: 13px;
  text-align: center;
}

/* ── Checkbox / dropdown 小修飾 ── */
.gr-check-radio input[type="checkbox"],
.gr-check-radio input[type="radio"] { accent-color: #c96442; }

/* 船艦勾選旁的全選 / 清空 button row */
.vessel-actions { gap: 6px !important; margin-top: -6px !important; margin-bottom: 4px !important; }
.vessel-actions button {
  flex: 0 0 auto !important;
  background: #ffffff !important;
  color: #36352f !important;
  border: 1px solid #d2cec1 !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  padding: 4px 12px !important;
  border-radius: 6px !important;
  min-width: 0 !important;
}
.vessel-actions button:hover { background: #f4f2eb !important; border-color: #c96442 !important; }

/* ── 滾動條（編輯感） ── */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #faf9f5; }
::-webkit-scrollbar-thumb { background: #d2cec1; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: #b5b0a3; }
"""


HERO_HTML = """
<div class="page-hero">
  <div class="eyebrow">海勤人力資源與作業安全決策 · INTERACTIVE</div>
  <h1>海事勤務互動分析介面</h1>
  <p class="lead">
    設定日期範圍、海域、船艦條件後點擊「執行分析」，系統會即時重跑 Pandas/SciPy/scikit-learn
    並輸出 21 張統計圖表、自動排班班表與決策建議。海況僅為輸入之一——真正的輸出是
    人員疲勞、工時公平、船艦可用性與明日排班決策。
  </p>
</div>
"""

FOOTER_HTML = """
<div class="page-footer">
  海象感知智慧排班與勤務決策平台 · 114-2 巨量資料與雲端運算 · 第 2 組
</div>
"""


def _rec_to_html(rec: dict) -> str:
    """將 compute_recommendations 結果轉為 Gradio HTML 顯示。"""
    if not rec:
        return "<p style='color:#9a948a;padding:24px;'>尚未產生建議，請先點擊「執行分析」。</p>"

    level_style = {
        "ok":   "background:#e8f5e9;border-left:3px solid #4caf50;color:#1b5e20;",
        "info": "background:#e3f2fd;border-left:3px solid #2196f3;color:#0d47a1;",
        "warn": "background:#fff3e0;border-left:3px solid #ff9800;color:#e65100;",
        "err":  "background:#fce4ec;border-left:3px solid #e91e63;color:#880e4f;",
    }

    parts = [
        "<div style='font-family:Inter,system-ui,sans-serif;padding:16px 0;'>",
        f"<p style='font-size:16px;font-weight:500;color:#141413;margin:0 0 16px;'>{rec.get('headline','')}</p>",
    ]

    # 即時海況 + 明日預測
    sn = rec.get("sea_now")
    ml = rec.get("ml_rough_tomorrow")
    if sn or ml is not None:
        chips = []
        if sn:
            chips.append(f"即時海況 <strong>{sn.get('sea_state','—')}</strong>（波高 {sn.get('wave_height','—')} m・{sn.get('obs_date','')}）")
        if ml is not None:
            chips.append(f"ML 預測明日惡劣海況 <strong>{ml}%</strong>")
        parts.append("<div style='background:#e3f2fd;border-left:3px solid #2196f3;color:#0d47a1;"
                     "padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:13.5px;'>"
                     + "　·　".join(chips) + "</div>")

    # 自動排班引擎：明日班表
    sched = rec.get("schedule") or {}
    if sched.get("assignments"):
        zs = sched.get("zone_slots", {})
        parts.append(f"<h3 style='font-size:14px;font-weight:600;color:#36352f;margin:18px 0 8px;'>"
                     f"自動排班引擎 · 明日班表（{sched.get('date','')}）</h3>")
        parts.append(f"<p style='font-size:12.5px;color:#9a948a;margin:0 0 8px;'>"
                     f"明日惡劣海況機率 {sched.get('rough_prob',0)}%　·　員額 港口 {zs.get('港口',0)} / 近海 {zs.get('近海',0)} / 外海 {zs.get('外海',0)}</p>")
        parts.append("<table style='width:100%;border-collapse:collapse;font-size:13px;'>")
        parts.append("<tr style='color:#9a948a;border-bottom:1px solid #e8e5dc;'>"
                     "<th style='text-align:left;padding:6px 4px;'>海域</th>"
                     "<th style='text-align:left;padding:6px 4px;'>人員</th>"
                     "<th style='text-align:left;padding:6px 4px;'>船艦</th>"
                     "<th style='text-align:right;padding:6px 4px;'>疲勞</th></tr>")
        for a in sched["assignments"]:
            fc = "color:#c0001e;font-weight:600;" if a["fatigue_score"] >= 65 else ""
            parts.append(f"<tr style='border-bottom:1px solid #f0ede5;'>"
                         f"<td style='padding:8px 4px;'>{a['zone']}</td>"
                         f"<td style='padding:8px 4px;font-weight:500;'>{a['name']}</td>"
                         f"<td style='padding:8px 4px;font-family:monospace;font-size:12px;'>{a['vessel']}</td>"
                         f"<td style='text-align:right;padding:8px 4px;{fc}'>{a['fatigue_score']}</td></tr>")
        parts.append("</table>")
        if sched.get("maintenance_vessels"):
            parts.append(f"<p style='font-size:12.5px;color:#e65100;margin:8px 0 0;'>"
                         f"維護中船艦（已排除）：{'、'.join(sched['maintenance_vessels'])}</p>")

    # 警示
    for al in rec.get("alerts", []):
        s = level_style.get(al.get("level", "info"), level_style["info"])
        parts.append(f"<div style='{s}padding:10px 14px;border-radius:6px;margin-bottom:8px;font-size:13.5px;'>{al['text']}</div>")

    # 海域風險表
    zr = rec.get("zone_risk", [])
    if zr:
        parts.append("<h3 style='font-size:14px;font-weight:600;color:#36352f;margin:20px 0 8px;'>各海域近 30 天海況</h3>")
        parts.append("<table style='width:100%;border-collapse:collapse;font-size:13px;'>")
        parts.append("<tr style='color:#9a948a;border-bottom:1px solid #e8e5dc;'>"
                     "<th style='text-align:left;padding:6px 4px;'>海域</th>"
                     "<th style='text-align:right;padding:6px 4px;'>次數</th>"
                     "<th style='text-align:right;padding:6px 4px;'>平均工時</th>"
                     "<th style='text-align:right;padding:6px 4px;'>大浪%</th></tr>")
        for z in zr:
            c = "color:#c96442;font-weight:600;" if z["rough_pct"] > 20 else ""
            parts.append(f"<tr style='border-bottom:1px solid #f0ede5;'>"
                         f"<td style='padding:8px 4px;font-weight:500;'>{z['zone']}</td>"
                         f"<td style='text-align:right;padding:8px 4px;'>{z['count']}</td>"
                         f"<td style='text-align:right;padding:8px 4px;'>{z['avg_hours']} h</td>"
                         f"<td style='text-align:right;padding:8px 4px;{c}'>{z['rough_pct']}%</td></tr>")
        parts.append("</table>")

    # 人員暴露排名（top 8）
    er = rec.get("exposure_ranking", [])[:8]
    if er:
        parts.append("<h3 style='font-size:14px;font-weight:600;color:#36352f;margin:20px 0 8px;'>人員外海暴露排名（近 30 天 Top 8）</h3>")
        parts.append("<table style='width:100%;border-collapse:collapse;font-size:13px;'>")
        parts.append("<tr style='color:#9a948a;border-bottom:1px solid #e8e5dc;'>"
                     "<th style='text-align:left;padding:6px 4px;'>人員 ID</th>"
                     "<th style='text-align:right;padding:6px 4px;'>次數</th>"
                     "<th style='text-align:right;padding:6px 4px;'>外海%</th>"
                     "<th style='text-align:right;padding:6px 4px;'>大浪%</th></tr>")
        for e in er:
            oc = "color:#c96442;font-weight:600;" if e["offshore_pct"] > 50 else ""
            rc = "color:#c96442;font-weight:600;" if e["rough_sea_pct"] > 20 else ""
            parts.append(f"<tr style='border-bottom:1px solid #f0ede5;'>"
                         f"<td style='padding:8px 4px;font-family:monospace;font-size:12px;'>{e['user_id']}</td>"
                         f"<td style='text-align:right;padding:8px 4px;'>{e['records']}</td>"
                         f"<td style='text-align:right;padding:8px 4px;{oc}'>{e['offshore_pct']}%</td>"
                         f"<td style='text-align:right;padding:8px 4px;{rc}'>{e['rough_sea_pct']}%</td></tr>")
        parts.append("</table>")

    # 人員輪換建議
    rs = rec.get("rotation_suggestions", [])
    if rs:
        parts.append("<h3 style='font-size:14px;font-weight:600;color:#36352f;margin:20px 0 8px;'>人員輪換建議</h3>")
        parts.append("<table style='width:100%;border-collapse:collapse;font-size:13px;'>")
        parts.append("<tr style='color:#9a948a;border-bottom:1px solid #e8e5dc;'>"
                     "<th style='text-align:left;padding:6px 4px;'>姓名</th>"
                     "<th style='text-align:right;padding:6px 4px;'>外海%</th>"
                     "<th style='text-align:right;padding:6px 4px;'>大浪%</th>"
                     "<th style='text-align:left;padding:6px 12px;'>建議行動</th></tr>")
        for r in rs:
            nc = "color:#c96442;font-weight:600;" if r["priority"] == "high" else ""
            ac = "color:#c96442;" if r["priority"] == "high" else "color:#1565c0;"
            parts.append(f"<tr style='border-bottom:1px solid #f0ede5;'>"
                         f"<td style='padding:8px 4px;font-weight:500;'>{r['name']}</td>"
                         f"<td style='text-align:right;padding:8px 4px;{nc}'>{r['offshore_pct']}%</td>"
                         f"<td style='text-align:right;padding:8px 4px;'>{r['rough_sea_pct']}%</td>"
                         f"<td style='padding:8px 12px;{ac}'>{r['action']}</td></tr>")
        parts.append("</table>")

    # Markov 預測摘要
    m7 = rec.get("markov_rough_7day")
    if m7 is not None:
        mc = "background:#fff3e0;border-left:3px solid #ff9800;color:#e65100;" if m7 > 15 else "background:#e3f2fd;border-left:3px solid #2196f3;color:#0d47a1;"
        parts.append(f"<div style='{mc}padding:10px 14px;border-radius:6px;margin-top:16px;font-size:13.5px;'>"
                     f"Markov 模型預測：未來 7 天大浪期望機率 <strong>{m7}%</strong></div>")

    ts = rec.get("generated_at", "")
    if ts:
        parts.append(f"<p style='font-size:12px;color:#9a948a;margin-top:16px;'>建議報告生成時間：{ts}</p>")

    parts.append("</div>")
    return "".join(parts)


def _load_rec_html(prefix: str = "") -> str:
    for fname in [f"{prefix}recommendations.json", "recommendations.json"]:
        p = OUTPUT_DIR / fname
        if p.exists():
            try:
                return _rec_to_html(json.loads(p.read_text("utf-8")))
            except Exception:
                pass
    return _rec_to_html(None)


# ── 建立介面 ──────────────────────────────────────────────────────────────────
opts = _load_options()

with gr.Blocks(title="海事勤務分析系統") as demo:
    gr.HTML(HERO_HTML)

    with gr.Row():
        with gr.Column(scale=1):
            gr.HTML('<div class="section-eyebrow">FILTERS · 篩選條件</div>')
            with gr.Group(elem_classes="filter-panel"):
                date_from_input = gr.Textbox(
                    label="開始日期",
                    value=str(opts["date_min"]) if opts["date_min"] else "2025-11-01",
                    placeholder="YYYY-MM-DD",
                )
                date_to_input = gr.Textbox(
                    label="結束日期",
                    value=str(opts["date_max"]) if opts["date_max"] else "2026-04-30",
                    placeholder="YYYY-MM-DD",
                )
                zone_input = gr.CheckboxGroup(
                    choices=ZONE_OPTIONS,
                    value=ZONE_OPTIONS,
                    label="值勤海域（全選等同無篩選）",
                )
                vessel_input = gr.CheckboxGroup(
                    choices=opts["vessels"],
                    value=opts["vessels"],
                    label="船艦（全選等同無篩選）",
                    elem_id="vessel-select",
                )
                with gr.Row(elem_classes="vessel-actions"):
                    vessel_all_btn = gr.Button("全選", size="sm", variant="secondary")
                    vessel_clr_btn = gr.Button("清空", size="sm", variant="secondary")
                run_btn = gr.Button("執行分析", variant="primary", size="lg")
                status_txt = gr.Textbox(
                    label="執行狀態", interactive=False, value="尚未執行",
                    elem_classes="status-box",
                )

        with gr.Column(scale=3):
            gr.HTML('<div class="section-eyebrow">RESULTS · 分析結果</div>')
            charts = []
            with gr.Tabs():
                with gr.Tab(label="勤務決策建議"):
                    rec_html = gr.HTML(value=_load_rec_html())

                for tab_def in CHART_TABS:
                    with gr.Tab(label=tab_def["label"]):
                        tab_files = tab_def["charts"]
                        for i in range(0, len(tab_files), 2):
                            with gr.Row():
                                charts.append(gr.Image(
                                    label=tab_files[i][1], type="filepath",
                                    elem_classes="chart-image",
                                ))
                                if i + 1 < len(tab_files):
                                    charts.append(gr.Image(
                                        label=tab_files[i + 1][1], type="filepath",
                                        elem_classes="chart-image",
                                    ))

    gr.HTML(FOOTER_HTML)

    def on_run(date_from, date_to, zones, vessels):
        v_filter = vessels if vessels and set(vessels) != set(opts["vessels"]) else None
        z_filter = zones if zones and set(zones) != set(ZONE_OPTIONS) else None
        try:
            paths = generate_charts(OUTPUT_DIR,
                                    date_from=date_from or None,
                                    date_to=date_to or None,
                                    zones=z_filter,
                                    vessels=v_filter)
            prefix = "filtered_" if any([date_from, date_to, z_filter, v_filter]) else ""
            path_map = {Path(p).name: p for p in paths}
            ordered = [path_map.get(f"{prefix}{f}", None) for f in CHART_FILES]
            rec = _load_rec_html(prefix)
            return ordered + [rec, "✅ 分析完成，圖表已更新"]
        except Exception as e:
            return [None] * len(CHART_LABELS) + [_rec_to_html(None), f"❌ 錯誤：{e}"]

    run_btn.click(
        fn=on_run,
        inputs=[date_from_input, date_to_input, zone_input, vessel_input],
        outputs=charts + [rec_html, status_txt],
    )
    vessel_all_btn.click(lambda: opts["vessels"], outputs=vessel_input)
    vessel_clr_btn.click(lambda: [], outputs=vessel_input)

if __name__ == "__main__":
    # 注意：Gradio 6.0 起 theme / css 由 Blocks 建構子移至 launch()，須在此傳入。
    # allowed_paths：Gradio 5/6 嚴格檔案存取，OUTPUT_DIR 若不在 cwd/temp 內
    # （如本機開發或自訂掛載點）會拒絕服務圖檔，需顯式允許。
    demo.launch(server_name="0.0.0.0", server_port=7860,
                theme=maritime_theme, css=CUSTOM_CSS,
                allowed_paths=[str(OUTPUT_DIR)])
