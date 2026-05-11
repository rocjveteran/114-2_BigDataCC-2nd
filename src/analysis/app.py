#!/usr/bin/env python3
"""
Gradio 互動分析介面。
提供篩選條件（日期、海域、船艦），即時產生圖表並顯示。
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


def run_analysis(date_from, date_to, zones, vessels, progress=gr.Progress()):
    progress(0, desc="連線資料庫...")

    df = str(date_from) if date_from else None
    dt = str(date_to)   if date_to   else None
    z  = list(zones)    if zones     else None
    v  = list(vessels)  if vessels   else None

    try:
        progress(0.1, desc="載入資料...")
        paths = generate_charts(OUTPUT_DIR, date_from=df, date_to=dt, zones=z, vessels=v)
        progress(1.0, desc="完成")
        return paths + [gr.update(visible=True), "✅ 分析完成"]
    except Exception as e:
        return [None] * 7 + [gr.update(visible=False), f"❌ 錯誤：{e}"]


# ── 建立介面 ──────────────────────────────────────────────────────────────────
opts = _load_options()

with gr.Blocks(title="海事勤務分析系統", theme=gr.themes.Base(primary_hue="blue")) as demo:
    gr.Markdown("# 海事勤務值勤分析系統\n操作步驟：設定篩選條件 → 點擊「執行分析」→ 查看圖表")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 篩選條件")
            date_from_input = gr.Textbox(
                label="開始日期（YYYY-MM-DD）",
                value=str(opts["date_min"]) if opts["date_min"] else "2025-11-01",
                placeholder="2025-11-01",
            )
            date_to_input = gr.Textbox(
                label="結束日期（YYYY-MM-DD）",
                value=str(opts["date_max"]) if opts["date_max"] else "2026-04-30",
                placeholder="2026-04-30",
            )
            zone_input = gr.CheckboxGroup(
                choices=ZONE_OPTIONS,
                value=ZONE_OPTIONS,
                label="值勤海域（不選 = 全部）",
            )
            vessel_input = gr.Dropdown(
                choices=["（全部）"] + opts["vessels"],
                value=["（全部）"],
                label="船艦篩選（可多選）",
                multiselect=True,
            )
            run_btn    = gr.Button("執行分析", variant="primary", size="lg")
            status_txt = gr.Textbox(label="狀態", interactive=False, value="尚未執行")

        with gr.Column(scale=3):
            gr.Markdown("### 分析結果")
            charts = []
            with gr.Row():
                charts.append(gr.Image(label=CHART_LABELS[0], type="filepath"))
                charts.append(gr.Image(label=CHART_LABELS[1], type="filepath"))
            with gr.Row():
                charts.append(gr.Image(label=CHART_LABELS[2], type="filepath"))
                charts.append(gr.Image(label=CHART_LABELS[3], type="filepath"))
            with gr.Row():
                charts.append(gr.Image(label=CHART_LABELS[4], type="filepath"))
                charts.append(gr.Image(label=CHART_LABELS[5], type="filepath"))
            with gr.Row():
                charts.append(gr.Image(label=CHART_LABELS[6], type="filepath"))

    result_row = gr.Row(visible=False)

    def on_run(date_from, date_to, zones, vessels):
        v_filter = [v for v in vessels if v != "（全部）"] or None
        z_filter = zones if zones else None
        try:
            paths = generate_charts(OUTPUT_DIR,
                                    date_from=date_from or None,
                                    date_to=date_to or None,
                                    zones=z_filter,
                                    vessels=v_filter)
            return paths + ["✅ 分析完成"]
        except Exception as e:
            import traceback
            return [None] * 7 + [f"❌ 錯誤：{e}\n{traceback.format_exc()}"]

    run_btn.click(
        fn=on_run,
        inputs=[date_from_input, date_to_input, zone_input, vessel_input],
        outputs=charts + [status_txt],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
