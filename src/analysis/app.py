#!/usr/bin/env python3
"""
Gradio 互動分析介面（第 16 週實作）。
目前為佔位啟動檔，確保容器不會因找不到 app.py 而退出。
"""

import gradio as gr

with gr.Blocks(title="海事勤務分析") as demo:
    gr.Markdown("## 海事勤務值勤分析系統\n\n互動介面開發中，預計第 16 週完成。")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
