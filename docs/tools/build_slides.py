# -*- coding: utf-8 -*-
"""
build_slides.py — 產生期末簡報 .pptx 草稿（16:9、16 張，依 docs/slides_outline.md）。
老師要求重點：流程架構圖與研究圖要做好 → 圖 1-3 + 7 張研究圖 + 系統截圖全嵌入。
執行：python3 docs/tools/build_slides.py
"""
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from lxml import etree

ROOT   = Path(__file__).resolve().parents[2]
FIG    = ROOT / "docs" / "figures"
CHART  = FIG / "charts"
SHOT   = ROOT / "docs" / "screenshots"
OUT    = ROOT / "docs" / "slides" / "第2組_海勤人力資源與作業安全決策系統_簡報草稿.pptx"

REC   = json.loads((FIG / "recommendations.json").read_text(encoding="utf-8"))
STATS = json.loads((FIG / "stats_summary.json").read_text(encoding="utf-8"))

NAVY, TEAL  = RGBColor(0x15, 0x29, 0x3E), RGBColor(0x0E, 0x7C, 0x7B)
GREEN, AMBER, RED = RGBColor(0x2E, 0x7D, 0x32), RGBColor(0xB4, 0x53, 0x09), RGBColor(0xB9, 0x1C, 0x1C)
GRAY, LIGHT = RGBColor(0x5B, 0x67, 0x70), RGBColor(0xF1, 0xF3, 0xF5)
WHITE, DARK = RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0x1A, 0x24, 0x30)
EA = "微軟正黑體"

SW, SH = Inches(13.333), Inches(7.5)
prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]


def _ea(run):
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", EA)


def textbox(slide, x, y, w, h, lines, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
            wrap=True):
    """lines: list of (text, size, bold, color) 或 (text, size, bold, color, space_after)"""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    first = True
    for item in lines:
        text, size, bold, color = item[:4]
        space_after = item[4] if len(item) > 4 else 4
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(space_after)
        r = p.add_run(); r.text = text
        r.font.size = Pt(size); r.font.bold = bold
        r.font.color.rgb = color; r.font.name = "Segoe UI"
        _ea(r)
    return tb


def rect(slide, x, y, w, h, fill, line_color=None, shadow=False, round_=False):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line_color is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line_color; shp.line.width = Pt(1)
    shp.shadow.inherit = shadow
    return shp


def image_fit(slide, path, x, y, max_w, max_h, border=False):
    im = Image.open(path); iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w, h = int(iw * scale), int(ih * scale)
    px = x + (max_w - w) // 2
    py = y + (max_h - h) // 2
    pic = slide.shapes.add_picture(str(path), px, py, width=w, height=h)
    if border:
        pic.line.color.rgb = RGBColor(0xD0, 0xD6, 0xDC); pic.line.width = Pt(1)
    return pic


def header(slide, eyebrow, title, num=None):
    rect(slide, 0, 0, SW, Inches(1.06), NAVY)
    rect(slide, 0, Inches(1.06), SW, Pt(3), TEAL)
    textbox(slide, Inches(0.55), Inches(0.12), Inches(11.0), Inches(0.3),
            [(eyebrow, 11, False, RGBColor(0x9F, 0xc5, 0xc4))])
    textbox(slide, Inches(0.55), Inches(0.40), Inches(11.0), Inches(0.6),
            [(title, 26, True, WHITE)])
    if num:
        textbox(slide, Inches(12.35), Inches(0.42), Inches(0.8), Inches(0.5),
                [(str(num), 16, True, RGBColor(0x6b, 0x80, 0x93))], align=PP_ALIGN.RIGHT)
    textbox(slide, Inches(0.55), Inches(7.12), Inches(9.0), Inches(0.3),
            [("114-2 巨量資料與雲端運算 · 第 2 組 · 海勤人力資源與作業安全決策系統",
              9, False, RGBColor(0xAa, 0xb4, 0xbc))])


def chip(slide, x, y, w, text, fill, text_color=WHITE, size=12, h=Inches(0.38)):
    shp = rect(slide, x, y, w, h, fill, round_=True)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Inches(0.06)
    tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = False
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = text_color
    r.font.name = "Segoe UI"; _ea(r)
    return shp


def mk_table(slide, x, y, w, h, headers, rows, col_w=None, size=13, head_size=13):
    t = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, w, h).table
    if col_w:
        total = sum(col_w)
        for j, cw in enumerate(col_w):
            t.columns[j].width = Emu(int(w * cw / total))
    for j, htxt in enumerate(headers):
        c = t.cell(0, j)
        c.fill.solid(); c.fill.fore_color.rgb = NAVY
        c.margin_left = c.margin_right = Inches(0.07)
        p = c.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = htxt
        r.font.size = Pt(head_size); r.font.bold = True; r.font.color.rgb = WHITE
        r.font.name = "Segoe UI"; _ea(r)
    for i, row in enumerate(rows, 1):
        for j, v in enumerate(row):
            c = t.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = WHITE if i % 2 else RGBColor(0xF6, 0xF8, 0xFA)
            c.margin_left = c.margin_right = Inches(0.07)
            p = c.text_frame.paragraphs[0]
            r = p.add_run(); r.text = str(v)
            r.font.size = Pt(size); r.font.color.rgb = DARK
            r.font.name = "Segoe UI"; _ea(r)
    return t


# ════ Slide 1｜封面 ═══════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, Inches(4.78), SW, Pt(2.5), TEAL)
textbox(s, Inches(0.9), Inches(1.55), Inches(11.5), Inches(1.6),
        [("海勤人力資源與作業安全決策系統", 44, True, WHITE, 10),
         ("海象感知智慧排班 · 海事勤務雲端管理平台", 20, False, RGBColor(0x9F, 0xC5, 0xC4))])
textbox(s, Inches(0.9), Inches(3.85), Inches(11.5), Inches(0.7),
        [("「別人把海象畫成圖，我們把海象變成『明天誰上哪艘船』。」", 17, True, RGBColor(0xE8, 0xC5, 0x7A))])
textbox(s, Inches(0.9), Inches(5.15), Inches(11.5), Inches(1.6),
        [("114-2 巨量資料與雲端運算 ── 第 2 組", 16, True, WHITE, 8),
         ("組長：黃宇平　　組員：傅瀚鋌・曾紹喆・劉家样・李翊丞・林秉賢", 14, False, RGBColor(0xC5, 0xCe, 0xD6), 8),
         ("指導老師：張珀銀 老師", 13, False, RGBColor(0x8A, 0x97, 0xA5))])

# ════ Slide 2｜與第 5 組差異 ══════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "DIFFERENTIATION", "我們與第 5 組（海象資料視覺化）不同在哪", 2)
mk_table(s, Inches(0.55), Inches(1.45), Inches(12.2), Inches(2.6),
         ["", "第 5 組", "第 2 組（我們）"],
         [["資料主角", "海象觀測值", "值勤紀錄 × 人員 × 船艦（海象只是輸入）"],
          ["核心問題", "海象怎麼分析、怎麼畫？", "海象惡劣時，明天該派誰、上哪艘船？"],
          ["系統本質", "分析／視覺化平台", "含打卡／請假／帳號的決策支援系統（DSS）"],
          ["招牌輸出", "海象趨勢圖", "自動排班引擎 → 明日值勤班表"]],
         col_w=[2.0, 3.6, 6.4], size=14)
textbox(s, Inches(0.55), Inches(4.45), Inches(12.2), Inches(0.5),
        [("他們做不到、我們才有的維度（皆需人員／船艦資料，純海象資料無法產出）：", 15, True, NAVY)])
items = [("人員疲勞指數", AMBER), ("工時公平 Gini + Lorenz", TEAL),
         ("船艦可用性與維護", RED), ("自動排班引擎（具名班表）", GREEN)]
x = Inches(0.55)
for txt, color in items:
    w = Inches(2.95)
    chip(s, x, Inches(5.05), w, txt, color, size=13, h=Inches(0.46))
    x += w + Inches(0.12)
textbox(s, Inches(0.55), Inches(5.85), Inches(12.2), Inches(0.6),
        [("全班唯一把海象接進人力資源排班決策的管理系統。", 18, True, NAVY)])

# ════ Slide 3｜問題與動機 ═════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "MOTIVATION", "問題與動機：從紀錄工具到決策工具", 3)
mk_table(s, Inches(0.55), Inches(1.5), Inches(12.2), Inches(2.9),
         ["上學期系統的問題（量化）", "本學期解法"],
         [["只能在 Windows XAMPP 執行，移機要重裝 ≥3 套軟體", "Docker 三容器，單一指令 60 秒啟動"],
          ["累積 1,200 筆紀錄、產出 0 張分析圖", "21 張統計圖 + 假設檢定 + ML 預測"],
          ["排班靠人工經驗，0 個決策因子被系統化", "排班引擎納入海況/疲勞/公平/船艦 4 因子"]],
         col_w=[6.0, 6.0], size=15)
textbox(s, Inches(0.55), Inches(4.8), Inches(12.2), Inches(1.8),
        [("海勤值勤的真實痛點：", 16, True, NAVY, 6),
         ("惡劣海況下外海作業風險陡增；人員疲勞累積是海事事故重要肇因（IMO 疲勞管理指引 MSC.1/Circ.1598）。", 14, False, DARK, 6),
         ("管理者要的不是更多報表，而是「明天該派誰、上哪艘船」的直接答案。", 15, True, TEAL)])

# ════ Slide 4｜系統架構 ═══════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "ARCHITECTURE", "系統架構：Docker Compose 三容器", 4)
image_fit(s, FIG / "fig1_architecture.png", Inches(0.7), Inches(1.3), Inches(9.2), Inches(5.6))
textbox(s, Inches(10.15), Inches(1.7), Inches(2.9), Inches(5.0),
        [("web", 15, True, TEAL, 2), ("php:8.2-apache\n打卡/請假/排班決策頁", 11, False, DARK, 10),
         ("db", 15, True, AMBER, 2), ("mysql:8.0\n4 張資料表", 11, False, DARK, 10),
         ("analysis", 15, True, GREEN, 2), ("python:3.11\nPandas / sklearn / Gradio", 11, False, DARK, 10),
         ("named volume", 13, True, GRAY, 2), ("21 張圖 + 班表 JSON\n+ Folium 地圖", 11, False, DARK)])

# ════ Slide 5｜技術清單 ═══════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "TECH STACK", "課程技術全覆蓋：必要 4 項 + 選擇 7 項", 5)
mk_table(s, Inches(0.55), Inches(1.4), Inches(5.95), Inches(2.6),
         ["必要技術", "用途"],
         [["Python + Pandas", "清洗/統計/排班引擎"],
          ["Matplotlib / Seaborn", "21 張視覺化圖表"],
          ["Docker", "三容器一鍵部署"],
          ["Git / GitHub", "版本管理 + CI"]],
         col_w=[2.6, 3.4], size=13)
mk_table(s, Inches(6.8), Inches(1.4), Inches(5.95), Inches(4.4),
         ["選擇性技術", "用途"],
         [["MySQL", "4 張資料表"],
          ["Apache + PHP", "業務系統 + 決策頁"],
          ["scikit-learn", "RandomForest 海況預測"],
          ["Folium", "互動海域地圖"],
          ["Gradio", "互動分析儀表板"],
          ["Jupyter Notebook", "探索式分析 EDA"],
          ["CWA 開放資料", "浮標海象（自動備援）"]],
         col_w=[2.6, 3.4], size=13)
textbox(s, Inches(0.55), Inches(4.45), Inches(5.95), Inches(2.0),
        [("33", 40, True, TEAL, 0), ("項自動化測試（GitHub Actions CI 全綠）", 13, False, DARK, 12),
         ("21+1", 40, True, AMBER, 0), ("張分析圖表（含 CWA 海象對照圖）", 13, False, DARK)])

# ════ Slide 6｜資料設計 ═══════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "DATA", "資料設計：海事業務欄位 + CWA 海象管線", 6)
textbox(s, Inches(0.55), Inches(1.35), Inches(6.1), Inches(2.3),
        [("attendance 擴充三欄位", 16, True, NAVY, 6),
         ("duty_zone　ENUM(港口/近海/外海)", 13, False, DARK, 3),
         ("sea_state　ENUM(平靜/輕浪/中浪/大浪)", 13, False, DARK, 3),
         ("vessel_id　MAR-001 ～ MAR-008", 13, False, DARK, 10),
         ("sea_observations（CWA 浮標）", 16, True, NAVY, 6),
         ("station / obs_date / wave_height / sea_temp / sea_state / data_source", 12, False, DARK)])
mk_table(s, Inches(0.55), Inches(4.0), Inches(6.1), Inches(2.5),
         ["資料表", "筆數", "說明"],
         [["attendance", "1,200", "6 個月值勤（動態生成）"],
          ["sea_observations", "724", "4 浮標站逐日海象"],
          ["leaves", "77", "請假申請"],
          ["users", "13", "三層級權限"]],
         col_w=[2.4, 1.2, 3.2], size=12)
image_fit(s, CHART / "sea_obs_comparison.png", Inches(6.95), Inches(1.35), Inches(6.0), Inches(5.2), border=True)

# ════ Slide 7｜資料清洗 ═══════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "DATA CLEANING", "資料清洗與品質控管", 7)
code_box = rect(s, Inches(0.55), Inches(1.5), Inches(12.2), Inches(1.9), RGBColor(0x10, 0x1A, 0x24), round_=True)
tf = code_box.text_frame; tf.word_wrap = True
tf.margin_left = tf.margin_right = Inches(0.25); tf.margin_top = Inches(0.18)
for i, ln in enumerate([
    'att = att.dropna(subset=["check_in","check_out","duty_zone","sea_state","vessel_id"])',
    'att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600',
    'att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]   # 剔除異常工時',
]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    r = p.add_run(); r.text = ln
    r.font.size = Pt(14); r.font.name = "Consolas"
    r.font.color.rgb = RGBColor(0x7F, 0xD4, 0xC2); _ea(r)
stats_items = [("1,200 → 1,200", "清洗後保留筆數（品質 100%）", TEAL),
               ("9.02 ± 0.81 h", "單次值勤工時 平均±標準差", NAVY),
               ("4.7%", "工時離群（>2σ）已標記覆核", AMBER)]
x = Inches(0.55)
for big, small, color in stats_items:
    rect(s, x, Inches(3.9), Inches(3.93), Inches(1.7), LIGHT, round_=True)
    textbox(s, x + Inches(0.25), Inches(4.12), Inches(3.5), Inches(1.3),
            [(big, 26, True, color, 4), (small, 12, False, GRAY)])
    x += Inches(4.13)
textbox(s, Inches(0.55), Inches(5.95), Inches(12.2), Inches(0.6),
        [("清洗規則以 33 項 pytest 測試鎖定行為，CI 每次推送自動驗證。", 14, False, DARK)])

# ════ Slide 8｜⭐ 自動排班引擎 ═══════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "⭐ CORE ENGINE", "核心：自動排班引擎 build_schedule()", 8)
image_fit(s, FIG / "fig3_engine.png", Inches(0.55), Inches(1.25), Inches(12.2), Inches(5.7))

# ════ Slide 9｜排班引擎實際輸出 ═══════════════════════════════════
s = prs.slides.add_slide(BLANK)
sch = REC.get("schedule", {})
header(s, "LIVE OUTPUT", f"引擎實際輸出：明日班表（{sch.get('date','')}）", 9)
zs = sch.get("zone_slots", {})
info = [(f"{sch.get('rough_prob')}%", "明日惡劣海況機率（ML）", AMBER),
        (f"{zs.get('港口')}/{zs.get('近海')}/{zs.get('外海')}", "港口/近海/外海 員額", TEAL),
        (f"{', '.join(sch.get('maintenance_vessels') or ['—'])}", "維護中船艦（自動排除）", RED)]
x = Inches(0.55)
for big, small, color in info:
    rect(s, x, Inches(1.35), Inches(3.93), Inches(1.15), LIGHT, round_=True)
    textbox(s, x + Inches(0.22), Inches(1.5), Inches(3.55), Inches(0.95),
            [(big, 21, True, color, 2), (small, 11, False, GRAY)])
    x += Inches(4.13)
rows = [[a["zone"], a["name"], a["vessel"], a["fatigue_score"], f"{a['offshore_pct']}%", a["reason"]]
        for a in sch.get("assignments", [])]
mk_table(s, Inches(0.55), Inches(2.75), Inches(12.2), Inches(3.6),
         ["海域", "人員", "船艦", "疲勞", "外海暴露", "指派理由"],
         rows, col_w=[1.0, 1.3, 1.4, 0.9, 1.2, 6.2], size=12, head_size=12)
textbox(s, Inches(0.55), Inches(6.55), Inches(12.2), Inches(0.5),
        [("以上為系統 recommendations.json 實際輸出 → scheduler.php 與 Gradio 同步呈現", 12, False, GRAY)])

# ════ Slide 10｜人力資源分析 ══════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "HR ANALYTICS", "人力資源分析（第 5 組做不出來的維度）", 10)
image_fit(s, CHART / "fatigue.png",             Inches(0.35), Inches(1.4),  Inches(6.4), Inches(2.75), border=True)
image_fit(s, CHART / "fairness_lorenz.png",     Inches(0.35), Inches(4.25), Inches(6.4), Inches(2.75), border=True)
image_fit(s, CHART / "vessel_availability.png", Inches(6.95), Inches(1.4),  Inches(6.05), Inches(2.75), border=True)
textbox(s, Inches(7.15), Inches(4.45), Inches(5.8), Inches(2.3),
        [("關鍵發現", 16, True, NAVY, 6),
         ("• 疲勞指數＝連續值勤＋7 日工時 → 0–100 分級", 13, False, DARK, 4),
         ("• Gini = 0.033：工時分配均勻，輪班制度合理", 13, False, DARK, 4),
         ("• MAR-007 達維護門檻 → 排班引擎自動排除", 13, False, DARK, 4),
         ("• 外海暴露率驅動公平輪換建議", 13, False, DARK)])

# ════ Slide 11｜海象智慧分析 ══════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "SEA-STATE INTELLIGENCE", "海象智慧分析（輸入端）", 11)
image_fit(s, CHART / "markov_heatmap.png",      Inches(0.35), Inches(1.4),  Inches(6.4), Inches(2.75), border=True)
image_fit(s, CHART / "feature_importance.png",  Inches(0.35), Inches(4.25), Inches(6.4), Inches(2.75), border=True)
image_fit(s, CHART / "zone_map_static.png",     Inches(6.95), Inches(1.4),  Inches(6.05), Inches(3.4), border=True)
textbox(s, Inches(7.15), Inches(5.0), Inches(5.8), Inches(1.8),
        [("Markov 7 日惡劣機率 6.4%・ML 明日 20.7%（互為驗證）", 13, True, NAVY, 5),
         ("RandomForest：準確率 92.3%、AUC 0.713", 13, True, TEAL, 5),
         ("互動版 Folium 地圖（duty_map.html）：海域多邊形 + 船艦 + CWA 浮標＋熱力圖", 12, False, DARK)])

# ════ Slide 12｜統計檢定 ══════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "STATISTICAL EVIDENCE", "統計檢定與建模結果（全部為實測輸出）", 12)
mk_table(s, Inches(0.55), Inches(1.5), Inches(12.2), Inches(4.4),
         ["分析項目", "統計量 / 指標", "結論"],
         [["海況對工時（ANOVA）", "F = 167.9，p < 0.0001", "海況顯著影響工時"],
          ["海域 × 海況（卡方檢定）", "χ² = 331.0（df=6），p < 0.0001", "外海大浪比例顯著高於港口"],
          ["工時驅動因子（OLS）", "R² = 0.778", "上工時刻與海況為最大因子"],
          ["明日惡劣海況（RandomForest）", "Accuracy 92.3%・AUC 0.713", "供排班引擎風險輸入"],
          ["工時公平性", "Gini = 0.033", "分配均勻，制度設計合理"]],
         col_w=[3.6, 4.2, 4.2], size=14)
textbox(s, Inches(0.55), Inches(6.2), Inches(12.2), Inches(0.6),
        [("資料：1,200 筆值勤（2025-12 ～ 2026-06）＋ 724 筆 CWA 浮標海象", 13, False, GRAY)])

# ════ Slide 13｜系統實機畫面 ══════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "LIVE SYSTEM", "PHP 業務系統 + 分析儀表板（實機截圖）", 13)
image_fit(s, SHOT / "01_login.png",                Inches(0.35), Inches(1.4),  Inches(4.2), Inches(2.6), border=True)
image_fit(s, SHOT / "03_admin_dashboard_hero.png", Inches(4.65), Inches(1.4),  Inches(4.2), Inches(2.6), border=True)
image_fit(s, SHOT / "05_charts.png",               Inches(8.95), Inches(1.4),  Inches(4.2), Inches(2.6), border=True)
image_fit(s, SHOT / "02_dashboard.png",            Inches(0.35), Inches(4.15), Inches(4.2), Inches(2.6), border=True)
image_fit(s, SHOT / "04_recommendations.png",      Inches(4.65), Inches(4.15), Inches(4.2), Inches(2.6), border=True)
image_fit(s, SHOT / "04_engine_map.png",           Inches(8.95), Inches(4.15), Inches(4.2), Inches(2.6), border=True)

# ════ Slide 14｜Docker 部署 ═══════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "DEPLOYMENT", "Docker 一鍵部署 Demo", 14)
code = rect(s, Inches(0.55), Inches(1.5), Inches(7.2), Inches(2.4), RGBColor(0x10, 0x1A, 0x24), round_=True)
tf = code.text_frame; tf.word_wrap = True
tf.margin_left = Inches(0.3); tf.margin_top = Inches(0.25)
for i, (ln, c) in enumerate([
    ("$ cp .env.example .env", RGBColor(0x7F, 0xD4, 0xC2)),
    ("$ cd docker", RGBColor(0x7F, 0xD4, 0xC2)),
    ("$ docker compose up --build", RGBColor(0xE8, 0xC5, 0x7A)),
    ("", WHITE),
    ("→ 約 60 秒後三容器就緒", RGBColor(0xC5, 0xCE, 0xD6)),
]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    r = p.add_run(); r.text = ln
    r.font.size = Pt(17); r.font.name = "Consolas"; r.font.color.rgb = c; _ea(r)
textbox(s, Inches(8.15), Inches(1.6), Inches(4.7), Inches(2.4),
        [("http://localhost:8080", 17, True, TEAL, 3),
         ("PHP 值勤系統 + 排班決策頁", 12, False, DARK, 14),
         ("http://localhost:7860", 17, True, AMBER, 3),
         ("Gradio 互動分析", 12, False, DARK)])
steps = ["[1/5] MySQL 初始化", "[2/5] 模擬資料生成", "[3/5] PHP 服務啟動", "[4/5] CWA 海象擷取", "[5/5] 21 張圖+引擎+地圖+ML"]
x = Inches(0.55)
for st in steps:
    chip(s, x, Inches(4.45), Inches(2.36), st, NAVY, size=10.5, h=Inches(0.42))
    x += Inches(2.46)
textbox(s, Inches(0.55), Inches(5.3), Inches(12.2), Inches(1.2),
        [("跨平台可重現：環境組態完全由 docker-compose.yml + .env 描述", 15, True, NAVY, 5),
         ("容器異常 → docker compose restart 數秒恢復（回應研究問題 1）", 13, False, DARK)])

# ════ Slide 15｜GitHub 管理 ═══════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "ENGINEERING", "GitHub 工程管理", 15)
mk_table(s, Inches(0.55), Inches(1.5), Inches(6.4), Inches(3.4),
         ["Commit 前綴", "範疇"],
         [["[docker]", "三容器 compose 配置"],
          ["[app]", "PHP 系統 + 排班決策頁"],
          ["[data]", "模擬資料 + CWA 海象管線"],
          ["[analysis]", "分析引擎 + 21 張圖 + ML"],
          ["[docs]", "報告 / 簡報 / 文件"],
          ["[fix] / [chore]", "修正與清理"]],
         col_w=[2.2, 4.2], size=13)
textbox(s, Inches(7.55), Inches(1.6), Inches(5.3), Inches(4.6),
        [("GitHub Actions CI", 18, True, NAVY, 6),
         ("每次 push 自動執行 33 項 pytest", 14, False, DARK, 14),
         ("安全規範", 18, True, NAVY, 6),
         ("• 連線設定全部走環境變數（getenv）", 13, False, DARK, 4),
         ("• .env / 金鑰不進版控（.gitignore）", 13, False, DARK, 4),
         ("• Demo 密碼以 CLI 工具重設，不寫死", 13, False, DARK)])

# ════ Slide 16｜結語 ══════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header(s, "CONCLUSION", "結語：海象 → 決策，完整交付", 16)
done = [
    "定位升級：海象視覺化 → 海勤人力資源與作業安全決策系統",
    "自動排班引擎（全班唯一，具名輸出明日班表）",
    "疲勞指數 / 工時公平 Gini 0.033 / 船艦可用性",
    "RandomForest 92.3% Acc・AUC 0.713 + Markov 互驗",
    "21+1 張統計圖 + Folium 互動地圖 + CWA 海象管線",
    "Docker 一鍵部署 + CI 33 測試全綠",
]
y = Inches(1.45)
for d in done:
    textbox(s, Inches(0.7), y, Inches(7.6), Inches(0.5),
            [("✔  " + d, 15, True, DARK)])
    y += Inches(0.62)
rect(s, Inches(8.6), Inches(1.45), Inches(4.2), Inches(3.6), LIGHT, round_=True)
textbox(s, Inches(8.9), Inches(1.7), Inches(3.7), Inches(3.2),
        [("未來展望", 17, True, NAVY, 8),
         ("• CWA 即時 API（金鑰機制已內建）", 13, False, DARK, 6),
         ("• 線性/整數規劃排班最佳化", 13, False, DARK, 6),
         ("• 行動裝置打卡與班表推播", 13, False, DARK)])
textbox(s, Inches(0.7), Inches(5.6), Inches(12.0), Inches(1.0),
        [("「別人把海象畫成圖，我們把海象變成『明天誰上哪艘船』。」", 20, True, TEAL)])

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
print(f"saved: {OUT}")
print(f"slides: {len(prs.slides.__iter__.__self__._sldIdLst)}  size: {OUT.stat().st_size/1024:.0f} KB")
