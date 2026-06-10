# -*- coding: utf-8 -*-
"""產出期末報告/PPT 用三張架構與流程圖（老師要求：流程架構與研究圖）"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle

font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc")
cjk = next(f.name for f in font_manager.fontManager.ttflist if "CJK" in f.name)
plt.rcParams["font.family"] = cjk
plt.rcParams["axes.unicode_minus"] = False
OUT = "/home/user/114-2_BigDataCC-2nd/docs/figures"

C_BLUE, C_TEAL, C_GRAY = "#1e5b8a", "#0e7c7b", "#5b6770"
C_GREEN, C_AMBER, C_RED = "#2e7d32", "#b45309", "#b91c1c"
C_BG_B, C_BG_T, C_BG_G = "#e8f1f8", "#e6f4f4", "#f1f3f5"
C_BG_GR, C_BG_A, C_BG_R = "#e9f5ea", "#fdf3e3", "#fdeaea"

def box(ax, x, y, w, h, text, fc, ec, fs=11, bold=True, tc="#1a2430", lw=1.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
                                fc=fc, ec=ec, lw=lw, zorder=3))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=tc, zorder=4, linespacing=1.45)

def arrow(ax, x1, y1, x2, y2, color="#42505e", lw=1.8, style="-|>"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=2,
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                shrinkA=2, shrinkB=2, mutation_scale=16))

def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=170)
    ax.set_xlim(0, 100); ax.set_ylim(0, 62); ax.axis("off")
    return fig, ax

# ── 圖1 系統架構 ─────────────────────────────────────
fig, ax = canvas(10.5, 6.4)
ax.text(50, 59.5, "系統架構：Docker Compose 三容器", ha="center", fontsize=15, fontweight="bold", color="#152333")
box(ax, 8, 47, 26, 7.5, "瀏覽器  http://localhost:8080\nPHP 值勤管理系統", "#ffffff", C_GRAY, 10.5)
box(ax, 66, 47, 26, 7.5, "瀏覽器  http://localhost:7860\nGradio 互動分析", "#ffffff", C_GRAY, 10.5)
ax.add_patch(Rectangle((3, 3), 94, 39.5, fill=False, ec="#8a97a5", lw=1.4, ls=(0, (5, 4)), zorder=1))
ax.text(5, 40.2, "Docker 內部網路（單一指令 docker compose up 啟動）", fontsize=9.5, color="#5b6770")
box(ax, 8, 27, 26, 10.5, "web 容器\nphp:8.2-apache\n打卡·請假·排班決策頁\nscheduler.php / 儀表板", C_BG_B, C_BLUE, 10)
box(ax, 66, 27, 26, 10.5, "analysis 容器\npython:3.11\nPandas·scikit-learn\nGradio·排班引擎", C_BG_T, C_TEAL, 10)
box(ax, 37.5, 27, 25, 10.5, "analysis_output\n（named volume）\n21 張 PNG·duty_map.html\nrecommendations.json", C_BG_G, C_GRAY, 9.2, bold=False)
box(ax, 37.5, 6.5, 25, 10.5, "db 容器\nmysql:8.0\nusers · attendance · leaves\nsea_observations", "#fdf6e9", "#9a7b2d", 10)
arrow(ax, 21, 47, 21, 38.3); arrow(ax, 79, 47, 79, 38.3)
arrow(ax, 23, 27, 40, 15.5); arrow(ax, 77, 27, 60, 15.5)
arrow(ax, 66, 32.2, 63.3, 32.2); arrow(ax, 37.5, 32.2, 34.8, 32.2)
ax.text(50, 1.0, "PHP 與 Python 連向同一 MySQL；分析產物經共用 volume 交付 PHP 前端嵌入顯示",
        ha="center", fontsize=9.5, color="#5b6770")
fig.savefig(f"{OUT}/fig1_architecture.png", bbox_inches="tight", facecolor="white"); plt.close(fig)

# ── 圖2 資料流程 ─────────────────────────────────────
fig, ax = canvas(12.5, 4.6)
ax.text(50, 58, "資料流程：從資料生成到決策呈現", ha="center", fontsize=15, fontweight="bold", color="#152333")
stages = [
    ("① 資料生成", "generate_mock_data.py\n約 1,200 筆值勤紀錄\nfetch_sea_data.py\nCWA 浮標 ≈720 筆海象", C_BG_B, C_BLUE),
    ("② 儲存", "MySQL 8.0\nusers / attendance\nleaves\nsea_observations", "#fdf6e9", "#9a7b2d"),
    ("③ 分析", "Pandas 清洗·統計檢定\nRandomForest·Markov\n排班引擎\nbuild_schedule()", C_BG_T, C_TEAL),
    ("④ 產出", "21 張 PNG 圖表\nduty_map.html（Folium）\nrecommendations.json\nsea_predictor.joblib", C_BG_G, C_GRAY),
    ("⑤ 呈現", "PHP 儀表板\nscheduler.php 明日排班\nGradio 互動介面\n（每 60 秒自動刷新）", C_BG_GR, C_GREEN),
]
w, gap, x = 17.6, 2.9, 2.0
for i, (t, sub, fc, ec) in enumerate(stages):
    xi = x + i * (w + gap)
    box(ax, xi, 14, w, 30, "", fc, ec)
    ax.text(xi + w/2, 38.5, t, ha="center", fontsize=12, fontweight="bold", color="#152333", zorder=5)
    ax.text(xi + w/2, 25, sub, ha="center", va="center", fontsize=8.8, color="#2a3540", zorder=5, linespacing=1.6)
    if i < 4:
        arrow(ax, xi + w + 0.7, 29, xi + w + gap - 0.7, 29, lw=2.2)
fig.savefig(f"{OUT}/fig2_dataflow.png", bbox_inches="tight", facecolor="white"); plt.close(fig)

# ── 圖3 排班決策引擎 ──────────────────────────────────
fig, ax = canvas(11.5, 6.4)
ax.text(50, 59.5, "自動排班決策引擎：四項輸入 → 決策規則 → 明日班表", ha="center", fontsize=15, fontweight="bold", color="#152333")
ins = [
    ("明日惡劣海況機率\nRandomForest + Markov", C_BG_B, C_BLUE),
    ("人員疲勞指數 0–100\n連續值勤 + 7 日工時", C_BG_A, C_AMBER),
    ("外海暴露率\n公平輪換（Gini·Lorenz）", C_BG_T, C_TEAL),
    ("船艦可用性\n維護里程（每 45 航次）", C_BG_G, C_GRAY),
]
ys = [45.5, 33.5, 21.5, 9.5]
for (t, fc, ec), y in zip(ins, ys):
    box(ax, 3, y, 25, 9, t, fc, ec, 9.8)
    arrow(ax, 28.6, y + 4.5, 34.4, y + 4.5)
box(ax, 35.5, 9.5, 29, 45, "", "#eef1f6", "#33415c", lw=2)
ax.text(50, 48.5, "build_schedule()", ha="center", fontsize=13.5, fontweight="bold", color="#1d2b45", zorder=5)
ax.text(50, 44.6, "自動排班引擎", ha="center", fontsize=10.5, color="#33415c", zorder=5)
ax.text(50, 27, "① 惡劣機率越高 → 外海員額越少\n\n② 外海優先派「低疲勞·低暴露」者\n\n③ 過勞者配置港口輕負荷\n\n④ 維護中船艦排除·每艦僅一組",
        ha="center", va="center", fontsize=9.8, color="#1d2b45", zorder=5, linespacing=1.5)
outs = [
    ("明日三海域具名班表\n（誰 · 哪海域 · 哪艘船）", C_BG_GR, C_GREEN),
    ("建議輪休名單\n（高疲勞人員）", C_BG_A, C_AMBER),
    ("維護中船艦清單", C_BG_R, C_RED),
    ("可用艦不足警示\nvessel_limited", C_BG_G, C_GRAY),
]
for (t, fc, ec), y in zip(outs, ys):
    arrow(ax, 65.1, y + 4.5, 70.9, y + 4.5)
    box(ax, 72, y, 25, 9, t, fc, ec, 9.8)
ax.text(50, 3.2, "輸出寫入 recommendations.json，由 scheduler.php 與 Gradio「人力資源決策」分頁同步呈現",
        ha="center", fontsize=9.5, color="#5b6770")
fig.savefig(f"{OUT}/fig3_engine.png", bbox_inches="tight", facecolor="white"); plt.close(fig)
print("done:", cjk)
