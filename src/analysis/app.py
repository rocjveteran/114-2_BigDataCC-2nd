#!/usr/bin/env python3
"""
Gradio 互動分析介面 — 視覺風格對齊 PHP 系統的編輯感主題。
"""

import os
from pathlib import Path
from datetime import date

import gradio as gr
from analysis import generate_charts, get_connection, get_filter_options

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))

CHART_LABELS = [
    "月度值勤人次趨勢",
    "值勤海域分布",
    "各海域海況分布",
    "各船艦值勤次數",
    "各海況值勤時數分布",
    "人員月度出勤熱力圖",
    "每月核准請假件數",
    "海域×海況平均工時",
    "異常值勤偵測（Z-score）",
    "週幾出勤模式",
    "船艦使用 Pareto 圖",
]

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
    body_background_fill="#faf9f5",
    body_text_color="#141413",
    background_fill_primary="#ffffff",
    background_fill_secondary="#faf9f5",
    border_color_primary="#e8e5dc",
    border_color_accent="#c96442",
    button_primary_background_fill="#c96442",
    button_primary_background_fill_hover="#b5502f",
    button_primary_text_color="#ffffff",
    button_primary_border_color="*primary_500",
    button_secondary_background_fill="#ffffff",
    button_secondary_background_fill_hover="#f1efe7",
    button_secondary_text_color="#141413",
    button_secondary_border_color="#e8e5dc",
    block_background_fill="#ffffff",
    block_border_color="#e8e5dc",
    block_border_width="1px",
    block_radius="10px",
    block_shadow="none",
    block_label_text_color="#6b6862",
    block_label_text_weight="500",
    block_label_text_size="13px",
    block_title_text_color="#141413",
    block_title_text_weight="500",
    input_background_fill="#ffffff",
    input_background_fill_focus="#ffffff",
    input_border_color="#e8e5dc",
    input_border_color_focus="#c96442",
    input_shadow_focus="0 0 0 3px rgba(201,100,66,0.1)",
    panel_background_fill="#ffffff",
    panel_border_color="#e8e5dc",
    color_accent_soft="rgba(201,100,66,0.08)",
)


# ── 自訂 CSS ──────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500&family=Inter:wght@400;500;600&family=Noto+Serif+TC:wght@400;500&display=swap');

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
.filter-panel {
  background: #ffffff !important;
  border: 1px solid #e8e5dc !important;
  border-radius: 10px !important;
  padding: 22px !important;
}

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

/* ── 滾動條（編輯感） ── */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #faf9f5; }
::-webkit-scrollbar-thumb { background: #d2cec1; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: #b5b0a3; }
"""


HERO_HTML = """
<div class="page-hero">
  <div class="eyebrow">資料分析 · INTERACTIVE</div>
  <h1>海事勤務互動分析介面</h1>
  <p class="lead">
    設定日期範圍、海域、船艦條件後點擊「執行分析」，系統會即時重跑 Pandas/SciPy
    並輸出 11 張統計圖表。所有圖表也會同步寫入分析儀表板，供管理者於 PHP 系統檢視。
  </p>
</div>
"""

FOOTER_HTML = """
<div class="page-footer">
  海事勤務值勤管理系統 · 114-2 巨量資料與雲端運算 · 第 2 組
</div>
"""


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
                vessel_input = gr.Dropdown(
                    choices=["（全部）"] + opts["vessels"],
                    value=["（全部）"],
                    label="船艦（可多選）",
                    multiselect=True,
                )
                run_btn = gr.Button("執行分析", variant="primary", size="lg")
                status_txt = gr.Textbox(
                    label="執行狀態", interactive=False, value="尚未執行",
                    elem_classes="status-box",
                )

        with gr.Column(scale=3):
            gr.HTML('<div class="section-eyebrow">RESULTS · 分析結果</div>')
            charts = []
            for i in range(0, len(CHART_LABELS), 2):
                with gr.Row():
                    charts.append(gr.Image(
                        label=CHART_LABELS[i], type="filepath",
                        elem_classes="chart-image",
                    ))
                    if i + 1 < len(CHART_LABELS):
                        charts.append(gr.Image(
                            label=CHART_LABELS[i + 1], type="filepath",
                            elem_classes="chart-image",
                        ))

    gr.HTML(FOOTER_HTML)

    def on_run(date_from, date_to, zones, vessels):
        v_filter = [v for v in vessels if v != "（全部）"] or None
        z_filter = zones if zones and set(zones) != set(ZONE_OPTIONS) else None
        try:
            paths = generate_charts(OUTPUT_DIR,
                                    date_from=date_from or None,
                                    date_to=date_to or None,
                                    zones=z_filter,
                                    vessels=v_filter)
            return paths + ["✅ 分析完成，圖表已更新"]
        except Exception as e:
            return [None] * len(CHART_LABELS) + [f"❌ 錯誤：{e}"]

    run_btn.click(
        fn=on_run,
        inputs=[date_from_input, date_to_input, zone_input, vessel_input],
        outputs=charts + [status_txt],
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0", server_port=7860,
        theme=maritime_theme, css=CUSTOM_CSS,
    )
