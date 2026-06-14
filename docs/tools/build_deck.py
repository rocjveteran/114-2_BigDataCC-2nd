#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海勤人力資源與作業安全決策系統 — 期末專題簡報（專業淺色版）
配色：普魯士藍 #1C3D5A / 淺藍 #B8CDD9 / 古金 #D4A24E（學術・報告）
設計語言：白底、留白、細線、行動式標題（結論而非標籤）、統一網格、柔和陰影、無 emoji
"""
import os, json
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml
from lxml import etree
from PIL import Image

# ─── 調色盤 ────────────────────────────────────────────────────────────────────
def H(s): return RGBColor.from_string(s)
INK    = H("1C3D5A")   # 普魯士藍 — 標題/結構/深字
INK2   = H("34506A")   # 次藍
BODY   = H("3D4D5A")   # 內文
MUTED  = H("7C8B97")   # 說明/註腳
FAINT  = H("AEBCC6")   # 極淡（大數字浮水印）
GOLD   = H("C8922E")   # 古金強調（白底對比）
GOLD_L = H("D4A24E")   # 淺金
TEAL   = H("4E8C8A")   # 正向（沉穩青）
TERRA  = H("BC5B41")   # 警示/差異（沉穩赤陶）
PANEL  = H("F3F7F9")   # 卡片淺底
PANEL2 = H("E9F0F4")   # 卡片次底
PANEL3 = H("FBF4E6")   # 金色淺底（重點框）
LINE   = H("D7E0E6")   # 框線/分隔
LINE2  = H("C5D2DA")   # 較深框線
WHITE  = H("FFFFFF")
NEARW  = H("FAFCFD")   # 近白底

FONT   = "Microsoft JhengHei"
FONT_M = "Consolas"

SW, SH = Inches(13.333), Inches(7.5)
ML     = Inches(0.7)            # 左邊界
MR     = Inches(0.7)            # 右邊界
CW     = SW - ML - MR           # 內容寬
CONTENT_TOP = Inches(1.95)
CONTENT_BOT = Inches(6.95)

IMG = "/tmp/demo_output"
SCR = "/home/user/114-2_BigDataCC-2nd/docs/screenshots"
FIG = "/home/user/114-2_BigDataCC-2nd/docs/figures"

prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]
_pageno = [0]

# ─── 低階輔助 ──────────────────────────────────────────────────────────────────
def slide():
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = WHITE
    return s

def _font(run, font, size, color, bold, italic):
    run.font.size = Pt(size); run.font.bold = bold; run.font.italic = italic
    run.font.color.rgb = color; run.font.name = font
    rPr = run._r.get_or_add_rPr()
    # 拉丁字用指定字型（含等寬 Consolas），中日韓字一律用微軟正黑體，避免等寬字型缺字成方框
    faces = {'a:latin': font, 'a:ea': FONT, 'a:cs': font}
    for tag, face in faces.items():
        e = rPr.find(qn(tag))
        if e is None:
            e = etree.SubElement(rPr, qn(tag))
        e.set('typeface', face)

def add_shadow(shape, blur=7, dist=3.5, dir_deg=90, color="1C3D5A", alpha=20):
    pass  # disabled — custom XML injection breaks PowerPoint file validation

def rect(s, l, t, w, h, fill=None, line=None, lw=0.75, rounded=False, radius=0.045, shadow=False):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                             l, t, w, h)
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line; shp.line.width = Pt(lw)
    if rounded:
        try: shp.adjustments[0] = radius
        except Exception: pass
    return shp

def hline(s, l, t, w, color=LINE, weight=1.0):
    ln = s.shapes.add_connector(2, l, t, l+w, t)
    ln.line.color.rgb = color; ln.line.width = Pt(weight)
    return ln

def vline(s, l, t, h, color=LINE, weight=1.0):
    ln = s.shapes.add_connector(2, l, t, l, t+h)
    ln.line.color.rgb = color; ln.line.width = Pt(weight)
    return ln

L, C, R = PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.RIGHT

def text(s, l, t, w, h, lines, size=14, color=BODY, bold=False, italic=False,
         font=FONT, align=L, anchor='t', leading=1.12, space_after=5, wrap=True):
    """lines: str 或 list[str|dict]。dict 可含 text,size,color,bold,italic,font,align,bullet,space_before"""
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = wrap
    tf.vertical_anchor = {'t':MSO_ANCHOR.TOP,'m':MSO_ANCHOR.MIDDLE,'b':MSO_ANCHOR.BOTTOM}[anchor]
    tf.margin_left=0; tf.margin_right=0; tf.margin_top=0; tf.margin_bottom=0
    if isinstance(lines, str): lines = [lines]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        d = ln if isinstance(ln, dict) else {'text': ln}
        p.alignment = d.get('align', align)
        p.line_spacing = d.get('leading', leading)
        p.space_after = Pt(d.get('space_after', space_after))
        if 'space_before' in d: p.space_before = Pt(d['space_before'])
        bullet = d.get('bullet')
        txt = d.get('text','')
        if bullet:
            rb = p.add_run(); _font(rb, font, d.get('size',size),
                                    d.get('bullet_color', GOLD), True, False)
            rb.text = bullet + "  "
        r = p.add_run(); r.text = txt
        _font(r, d.get('font',font), d.get('size',size), d.get('color',color),
              d.get('bold',bold), d.get('italic',italic))
    return tb

def fit_image(s, path, bl, bt, bw, bh, align='c', valign='m', border=True, shadow=True, pad=0):
    if not os.path.exists(path):
        rect(s, bl, bt, bw, bh, fill=PANEL, line=LINE)
        text(s, bl, bt, bw, bh, "（圖片）", color=MUTED, align=C, anchor='m')
        return None
    bl,bt,bw,bh = int(bl),int(bt),int(bw),int(bh)
    bl+=pad; bt+=pad; bw-=2*pad; bh-=2*pad
    iw, ih = Image.open(path).size
    bar, iar = bw/bh, iw/ih
    if iar > bar: w = bw; h = bw/iar
    else: h = bh; w = bh*iar
    l = bl + {'l':0,'c':(bw-w)/2,'r':bw-w}[align]
    t = bt + {'t':0,'m':(bh-h)/2,'b':bh-h}[valign]
    pic = s.shapes.add_picture(path, Emu(int(l)), Emu(int(t)), Emu(int(w)), Emu(int(h)))
    if border: pic.line.color.rgb = LINE2; pic.line.width = Pt(0.75)
    return pic

# ─── 版型元件 ──────────────────────────────────────────────────────────────────
def header(s, kicker, title, sub=None):
    text(s, ML, Inches(0.46), CW, Inches(0.3),
         [{'text':kicker.upper(),'size':12,'color':GOLD,'bold':True}])
    text(s, ML, Inches(0.74), CW, Inches(0.72),
         [{'text':title,'size':25,'color':INK,'bold':True}])
    hline(s, ML, Inches(1.55), Inches(0.62), color=GOLD, weight=2.4)
    if sub:
        text(s, ML+Inches(0.78), Inches(1.40), CW-Inches(0.78), Inches(0.34),
             [{'text':sub,'size':13.5,'color':MUTED}])

def footer(s, page=True):
    hline(s, ML, Inches(7.06), CW, color=LINE, weight=0.75)
    text(s, ML, Inches(7.12), Inches(9), Inches(0.3),
         [{'text':'海勤人力資源與作業安全決策系統  ·  114-2 巨量資料與雲端運算  第 2 組',
           'size':9.5,'color':MUTED}])
    if page:
        _pageno[0]+=1
        text(s, SW-MR-Inches(1.2), Inches(7.12), Inches(1.2), Inches(0.3),
             [{'text':f'{_pageno[0]:02d}','size':9.5,'color':MUTED,'align':R}], font=FONT_M)

def content_slide(kicker, title, sub=None):
    s = slide(); header(s, kicker, title, sub); footer(s); return s

def takeaway(s, label, body, l=ML, t=Inches(6.18), w=CW):
    """金色重點條：左金邊 + 淺金底"""
    h = Inches(0.62)
    rect(s, l, t, w, h, fill=PANEL3, line=None, rounded=True, radius=0.10)
    rect(s, l, t, Inches(0.09), h, fill=GOLD)
    text(s, l+Inches(0.28), t, Inches(1.5), h,
         [{'text':label,'size':12,'color':GOLD,'bold':True}], anchor='m')
    text(s, l+Inches(1.85), t, w-Inches(2.1), h,
         [{'text':body,'size':13,'color':INK,'bold':False}], anchor='m', leading=1.05)

def card(s, l, t, w, h, fill=PANEL, line=LINE, shadow=False, radius=0.05):
    return rect(s, l, t, w, h, fill=fill, line=line, rounded=True, radius=radius, shadow=shadow)

def kpi(s, l, t, w, h, value, label, sub=None, accent=GOLD, value_size=30):
    card(s, l, t, w, h, fill=WHITE, line=LINE, shadow=True)
    rect(s, l, t, w, Inches(0.06), fill=accent)
    text(s, l+Inches(0.18), t+Inches(0.24), w-Inches(0.36), Inches(0.66),
         [{'text':value,'size':value_size,'color':INK,'bold':True}], font=FONT_M, anchor='m')
    text(s, l+Inches(0.18), t+h-Inches(0.62), w-Inches(0.36), Inches(0.3),
         [{'text':label,'size':12.5,'color':BODY,'bold':True}])
    if sub:
        text(s, l+Inches(0.18), t+h-Inches(0.34), w-Inches(0.36), Inches(0.28),
             [{'text':sub,'size':10.5,'color':MUTED}])

def annotate(s, l, t, w, items, header_txt=None, size=12.5, gap=None):
    """右側註解清單。items: list[str|dict]"""
    y = t
    if header_txt:
        text(s, l, y, w, Inches(0.34), [{'text':header_txt,'size':13.5,'color':INK,'bold':True}])
        hline(s, l, y+Inches(0.36), w, color=LINE)
        y += Inches(0.5)
    paras=[]
    for it in items:
        if isinstance(it, dict): paras.append(it)
        elif it=='': paras.append({'text':'','size':6,'space_after':2})
        elif it.startswith('· '):
            paras.append({'text':it[2:],'size':size-1.5,'color':MUTED,'bullet':'–','bullet_color':LINE2})
        else:
            paras.append({'text':it,'size':size,'color':BODY,'bullet':'▪','bullet_color':GOLD})
    text(s, l, y, w, Inches(5), paras, leading=1.12, space_after=6)

def table(s, l, t, col_w, header_row, rows, header_h=Inches(0.46), row_h=Inches(0.46),
          header_fill=INK, header_color=WHITE, fsize=12.5, hsize=12.5):
    x=l
    # header
    for i,htxt in enumerate(header_row):
        rect(s, x, t, col_w[i], header_h, fill=header_fill)
        align = header_row[i][1] if isinstance(header_row[i],tuple) else L
        htext = header_row[i][0] if isinstance(header_row[i],tuple) else htxt
        text(s, x+Inches(0.12), t, col_w[i]-Inches(0.2), header_h,
             [{'text':htext,'size':hsize,'color':header_color,'bold':True,'align':align}], anchor='m')
        x+=col_w[i]
    # rows
    y=t+header_h
    for r,row in enumerate(rows):
        x=l
        rfill = WHITE if r%2==0 else PANEL
        rect(s, l, y, sum(col_w), row_h, fill=rfill)
        for i,cell in enumerate(row):
            if isinstance(cell, tuple):
                ctxt, ccolor = cell[0], cell[1]
                calign = cell[2] if len(cell)>2 else L
                cbold = cell[3] if len(cell)>3 else False
            else:
                ctxt, ccolor, calign, cbold = cell, BODY, L, False
            cfont = FONT_M if (isinstance(cell,tuple) and len(cell)>4 and cell[4]=='m') else FONT
            text(s, x+Inches(0.12), y, col_w[i]-Inches(0.2), row_h,
                 [{'text':ctxt,'size':fsize,'color':ccolor,'bold':cbold,'align':calign,'font':cfont}],
                 anchor='m')
            x+=col_w[i]
        y+=row_h
    rect(s, l, t, sum(col_w), header_h+row_h*len(rows), fill=None, line=LINE)
    return y

# ─── 章節分隔頁（淺色・含小目錄）────────────────────────────────────────────────
def divider(num, zh, en, topics):
    s = slide()
    rect(s, 0, 0, Inches(0.16), SH, fill=INK)               # 左細邊
    # 大號浮水印數字
    text(s, Inches(0.5), Inches(0.9), Inches(5), Inches(3.2),
         [{'text':num,'size':200,'color':PANEL2,'bold':True}], font=FONT_M, anchor='m')
    text(s, Inches(0.95), Inches(3.05), Inches(7), Inches(0.32),
         [{'text':'SECTION '+num,'size':13,'color':GOLD,'bold':True}], font=FONT_M)
    text(s, Inches(0.95), Inches(3.40), Inches(8.5), Inches(0.9),
         [{'text':zh,'size':36,'color':INK,'bold':True}])
    text(s, Inches(0.95), Inches(4.45), Inches(8.5), Inches(0.4),
         [{'text':en,'size':15,'color':MUTED}], font=FONT_M)
    hline(s, Inches(0.97), Inches(4.30), Inches(3.0), color=GOLD, weight=2.4)
    # 右側本章重點
    rx = Inches(8.7); rw = Inches(4.0)
    text(s, rx, Inches(1.5), rw, Inches(0.34),
         [{'text':'本章內容','size':12,'color':GOLD,'bold':True}])
    hline(s, rx, Inches(1.86), rw, color=LINE)
    paras=[{'text':tp,'size':13,'color':BODY,'bullet':'▪','bullet_color':GOLD} for tp in topics]
    text(s, rx, Inches(2.04), rw, Inches(4.5), paras, leading=1.2, space_after=11)
    footer(s, page=False)
    return s

# ════════════════════════════════════════════════════════════════════════════
# 1. 封面
# ════════════════════════════════════════════════════════════════════════════
s = slide()
hline(s, 0, Inches(0.0), SW, color=GOLD, weight=3)
rect(s, 0, 0, Inches(0.16), SH, fill=INK)
text(s, ML, Inches(0.7), CW, Inches(0.32),
     [{'text':'國立高雄科技大學 · 海事資訊科技系','size':14,'color':MUTED}])
text(s, ML, Inches(1.5), Inches(11.5), Inches(1.7),
     [{'text':'海勤人力資源與','size':46,'color':INK,'bold':True,'space_after':2},
      {'text':'作業安全決策系統','size':46,'color':INK,'bold':True}], leading=1.05)
text(s, ML, Inches(3.45), CW, Inches(0.5),
     [{'text':'海象感知智慧排班 · 海事勤務雲端管理平台','size':20,'color':GOLD,'bold':True}])
# info row
text(s, ML, Inches(4.3), Inches(8), Inches(0.9),
     [{'text':'114-2 巨量資料與雲端運算　|　第 2 組','size':14,'color':INK,'bold':True,'space_after':4},
      {'text':'組員　黃宇平（組長）· 傅瀚鋌 · 曾紹喆 · 劉家样 · 李翊丞 · 林秉賢','size':12.5,'color':BODY,'space_after':3},
      {'text':'指導教師　張珀銀 老師　　　2026 年 6 月','size':12.5,'color':MUTED}])
# KPI strip bottom-right
kdata=[("25","分析圖表"),("45","CI 測試"),("0.811","ML AUC"),("0%","MILP 差距")]
kx=Inches(8.55)

for i,(v,l) in enumerate(kdata):
    x=kx+Inches(i*1.18)
    if i>0: vline(s, x-Inches(0.05), Inches(5.45), Inches(0.95), color=LINE)
    text(s, x, Inches(5.4), Inches(1.1), Inches(0.55),
         [{'text':v,'size':24,'color':GOLD,'bold':True,'align':C}], font=FONT_M)
    text(s, x, Inches(6.05), Inches(1.1), Inches(0.3),
         [{'text':l,'size':11,'color':MUTED,'align':C}])
hline(s, ML, Inches(6.95), CW, color=LINE)
text(s, ML, Inches(7.05), CW, Inches(0.3),
     [{'text':'MILP 整數規劃排班 · RandomForest 海況預測 · Isolation Forest 異常偵測 · Gradio 互動分析',
       'size':10.5,'color':MUTED}])

# ════════════════════════════════════════════════════════════════════════════
# 2. 一句話定位（大圖式）
# ════════════════════════════════════════════════════════════════════════════
s = content_slide("核心定位 · POSITIONING", "海象只是輸入，輸出是「明天誰上哪艘船」")
# 三段式流程：輸入 → 引擎 → 輸出
bx=ML; by=Inches(2.5); bw=Inches(3.55); bh=Inches(2.4); gap=Inches(0.55)
arrow_w=Inches(0.55)
cols=[
    ("輸入 INPUT", INK, ["明日海況預測（ML / Markov）","人員疲勞指數","外海暴露輪換","船艦可用性"]),
    ("引擎 ENGINE", GOLD, ["MILP 整數線性規劃","scipy.optimize.milp","HiGHS 後端","ZONE_PRIORITY 加權"]),
    ("輸出 OUTPUT", TEAL, ["明日三海域具名班表","建議輪休名單","維護船艦排除","決策可追溯理由"]),
]
for i,(t_,acc,items) in enumerate(cols):
    x=bx+Inches(i)*(bw+arrow_w+gap-gap)+Inches(i*0.0)
    x=bx+ (bw+arrow_w)*i + Inches(i*0.15)
    card(s, x, by, bw, bh, fill=WHITE, line=LINE, shadow=True)
    rect(s, x, by, bw, Inches(0.07), fill=acc)
    text(s, x, by+Inches(0.22), bw, Inches(0.4),
         [{'text':t_,'size':15,'color':acc,'bold':True,'align':C}], font=FONT_M)
    text(s, x+Inches(0.3), by+Inches(0.78), bw-Inches(0.5), Inches(1.5),
         [{'text':v,'size':12.5,'color':BODY,'bullet':'▪','bullet_color':acc} for v in items],
         leading=1.15, space_after=7)
    if i<2:
        text(s, x+bw, by, arrow_w+Inches(0.15), bh,
             [{'text':'→','size':30,'color':GOLD,'bold':True,'align':C}], anchor='m')
takeaway(s, "核心", "本系統整合值勤、人員、船艦、海象四類資料，最終輸出可執行的明日具名班表。")

# ════════════════════════════════════════════════════════════════════════════
# 3. 目錄
# ════════════════════════════════════════════════════════════════════════════
s = content_slide("簡報大綱 · AGENDA", "從研究背景到決策引擎的完整技術鏈")
agenda=[
    ("01","研究背景與動機","上學期成果 · 三大不足 · 量化研究問題"),
    ("02","系統架構與部署","Docker 三容器 · 技術選型 · 一鍵部署"),
    ("03","PHP 應用系統","業務功能 · 權限分層 · 操作 Demo"),
    ("04","核心：自動排班引擎","MILP 最佳化 · 決策規則 · 實機班表"),
    ("05","資料工程","Schema · AR(1) 模擬 · 清洗品質"),
    ("06","統計分析","ANOVA · 卡方 · OLS · 相關矩陣"),
    ("07","預測與機器學習","Holt · RandomForest · Markov · 異常偵測"),
    ("08","人力資源決策","疲勞 · 公平性 · 船艦 · 雷達圖"),
    ("09","互動介面與工程品質","Gradio · Folium · GitHub CI · 總結"),
]
cw2=(CW-Inches(0.6))/3; chh=Inches(1.42); gx=Inches(0.3); gy=Inches(0.3)
for i,(n,t_,d) in enumerate(agenda):
    col=i%3; row=i//3
    x=ML+col*(cw2+gx); y=Inches(2.15)+row*(chh+gy)
    card(s, x, y, cw2, chh, fill=WHITE, line=LINE, shadow=True)
    text(s, x+Inches(0.22), y+Inches(0.16), Inches(1.2), Inches(0.7),
         [{'text':n,'size':30,'color':PANEL2 if False else GOLD,'bold':True}], font=FONT_M)
    text(s, x+Inches(1.15), y+Inches(0.2), cw2-Inches(1.3), Inches(0.4),
         [{'text':t_,'size':14.5,'color':INK,'bold':True}])
    text(s, x+Inches(1.15), y+Inches(0.66), cw2-Inches(1.3), Inches(0.6),
         [{'text':d,'size':10.5,'color':MUTED}], leading=1.1)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 01
# ════════════════════════════════════════════════════════════════════════════
divider("01","研究背景與動機","Background & Motivation",
        ["上學期系統成果回顧","三項主要不足","量化研究問題","量化研究目的"])

# 1-1 上學期成果與不足
s = content_slide("研究背景 · 上學期成果", "從「紀錄工具」到「決策工具」的躍遷")
# 左：成果
lw=Inches(5.7)
card(s, ML, Inches(2.05), lw, Inches(4.0), fill=PANEL, line=LINE)
text(s, ML+Inches(0.3), Inches(2.25), lw-Inches(0.6), Inches(0.4),
     [{'text':'114-1 已完成（PHP + MySQL 雛形）','size':15,'color':INK,'bold':True}])
hline(s, ML+Inches(0.3), Inches(2.7), lw-Inches(0.6), color=LINE2)
text(s, ML+Inches(0.3), Inches(2.85), lw-Inches(0.6), Inches(3.0),
     [{'text':v,'size':13,'color':BODY,'bullet':'▪','bullet_color':TEAL} for v in
      ["登入認證與 Session 管理","值勤打卡（上 / 下勤）","請假申請與審核流程",
       "三層級權限（老闆 / 管理員 / 員工）","共 22 個 PHP 檔案，運行於 XAMPP"]],
     leading=1.2, space_after=12)
# 右：三大不足
rx=ML+lw+Inches(0.5); rw=CW-lw-Inches(0.5)
text(s, rx, Inches(2.05), rw, Inches(0.4),
     [{'text':'三項主要不足','size':15,'color':TERRA,'bold':True}])
defs=[("部署侷限","強依賴 Windows + XAMPP，無法跨平台移轉，不符雲端運維。"),
      ("缺乏分析","累積 1,200 筆紀錄卻產出 0 張圖表，管理層無從掌握趨勢。"),
      ("業務特性不足","通用打卡 schema，未反映海域 / 海況 / 船艦等海事維度。")]
for i,(t_,d) in enumerate(defs):
    y=Inches(2.55)+i*Inches(1.18)
    card(s, rx, y, rw, Inches(1.0), fill=WHITE, line=LINE, shadow=True)
    rect(s, rx, y, Inches(0.08), Inches(1.0), fill=TERRA)
    text(s, rx+Inches(0.25), y+Inches(0.12), rw-Inches(0.45), Inches(0.35),
         [{'text':f"{i+1}　{t_}",'size':13.5,'color':INK,'bold':True}])
    text(s, rx+Inches(0.25), y+Inches(0.5), rw-Inches(0.45), Inches(0.45),
         [{'text':d,'size':11.5,'color':BODY}], leading=1.1)

# 1-2 研究問題
s = content_slide("研究背景 · 研究問題", "三個可量化的問題，對應三個明確目標")
probs=[("環境不可重現","原系統綁定 Windows + XAMPP，移轉新主機須手動安裝 Apache / PHP / MySQL 至少 3 套軟體，組態不可重現，異常時無法快速復原。"),
       ("有資料、無洞察","系統累積 1,200 筆值勤紀錄，卻產出 0 張分析圖表；管理層無法掌握工時負荷、海況與值勤量關聯，更無任何預測能力。"),
       ("排班全憑經驗","排班未納入海況風險、人員疲勞、工時公平、船艦維護等至少 4 項決策因子，惡劣海況時段無法系統性縮減外海派遣員額。")]
for i,(t_,d) in enumerate(probs):
    y=Inches(2.15)+i*Inches(1.45)
    card(s, ML, y, CW, Inches(1.25), fill=WHITE, line=LINE, shadow=True)
    rect(s, ML, y, Inches(1.15), Inches(1.25), fill=INK, rounded=False)
    text(s, ML, y, Inches(1.15), Inches(1.25),
         [{'text':f'Q{i+1}','size':30,'color':WHITE,'bold':True,'align':C}], font=FONT_M, anchor='m')
    text(s, ML+Inches(1.4), y+Inches(0.16), CW-Inches(1.7), Inches(0.4),
         [{'text':t_,'size':15,'color':INK,'bold':True}])
    text(s, ML+Inches(1.4), y+Inches(0.58), CW-Inches(1.7), Inches(0.6),
         [{'text':d,'size':12.5,'color':BODY}], leading=1.12)

# 1-3 研究目的
s = content_slide("研究背景 · 研究目的", "對應問題設定三項可驗證的量化目標")
goals=[("跨平台容器化","docker compose up 單一指令完成 web / db / analysis 三容器部署，啟動 < 60 秒，異常可一鍵重建。","對應 Q1"),
       ("資料分析能力","Pandas 清洗 1,200 筆值勤 + 736 筆海象，產出 25 張涵蓋描述統計、檢定、預測、ML 的圖表，並附 Gradio 互動。","對應 Q2"),
       ("自動排班決策","build_schedule() 綜合 ML 海況預測、疲勞指數、外海暴露公平、船艦可用性 4 項輸入，自動產出明日具名班表。","對應 Q3")]
gw=(CW-Inches(0.7))/3
for i,(t_,d,tag) in enumerate(goals):
    x=ML+i*(gw+Inches(0.35))
    card(s, x, Inches(2.15), gw, Inches(3.7), fill=WHITE, line=LINE, shadow=True)
    rect(s, x, Inches(2.15), gw, Inches(0.07), fill=GOLD)
    text(s, x+Inches(0.25), Inches(2.45), gw-Inches(0.5), Inches(0.5),
         [{'text':f'目標 {i+1}','size':12,'color':GOLD,'bold':True}], font=FONT_M)
    text(s, x+Inches(0.25), Inches(2.85), gw-Inches(0.5), Inches(0.5),
         [{'text':t_,'size':16,'color':INK,'bold':True}])
    hline(s, x+Inches(0.25), Inches(3.4), gw-Inches(0.5), color=LINE)
    text(s, x+Inches(0.25), Inches(3.55), gw-Inches(0.5), Inches(1.9),
         [{'text':d,'size':12.5,'color':BODY}], leading=1.25)
    rect(s, x+Inches(0.25), Inches(5.35), Inches(1.3), Inches(0.34), fill=PANEL2, rounded=True, radius=0.3)
    text(s, x+Inches(0.25), Inches(5.35), Inches(1.3), Inches(0.34),
         [{'text':tag,'size':11,'color':INK2,'bold':True,'align':C}], anchor='m')

# ════════════════════════════════════════════════════════════════════════════
# SECTION 02
# ════════════════════════════════════════════════════════════════════════════
divider("02","系統架構與部署","Architecture & Deployment",
        ["Docker 三容器架構","技術選型理由","一鍵部署流程","資料處理管線"])

# 2-1 架構圖
s = content_slide("系統架構 · ARCHITECTURE", "三容器各司其職，共用網路與資料卷")
fit_image(s, f"{FIG}/fig1_architecture.png", ML, Inches(2.0), Inches(7.6), Inches(4.6))
rx=ML+Inches(7.9); rw=CW-Inches(7.9)
specs=[("web","php:8.2-apache · :8080","22 個 PHP 檔 · 打卡 / 請假 / 排班 / 帳號", INK),
       ("db","mysql:8.0 · 內部網路","4 張資料表 · db_data 卷持久化", INK2),
       ("analysis","python:3.11 · :7860","Pandas / ML / Gradio · 25 圖表", TEAL)]
for i,(t_,sub,d,acc) in enumerate(specs):
    y=Inches(2.0)+i*Inches(1.35)
    card(s, rx, y, rw, Inches(1.2), fill=WHITE, line=LINE, shadow=True)
    rect(s, rx, y, Inches(0.08), Inches(1.2), fill=acc)
    text(s, rx+Inches(0.25), y+Inches(0.13), rw-Inches(0.4), Inches(0.34),
         [{'text':t_,'size':15,'color':acc,'bold':True,'font':FONT_M}])
    text(s, rx+Inches(0.25), y+Inches(0.5), rw-Inches(0.4), Inches(0.3),
         [{'text':sub,'size':11,'color':MUTED,'font':FONT_M}])
    text(s, rx+Inches(0.25), y+Inches(0.8), rw-Inches(0.4), Inches(0.34),
         [{'text':d,'size':11.5,'color':BODY}])
takeaway(s, "資料交換", "analysis_output named volume 讓圖表與班表跨容器共用；連線憑證以 .env 注入，不寫死於程式碼。")

# 2-2 技術選型
s = content_slide("系統架構 · 技術選型", "每一層的選擇都有明確理由")
table(s, ML, Inches(2.1),
      [Inches(2.0), Inches(3.3), Inches(6.633)],
      [("層次",L),("技術",L),("選用理由",L)],
      [[("前端",INK,L,True),"PHP 8.2 + Apache","延用上學期成果，降低重寫成本、聚焦本學期分析與決策"],
       [("資料庫",INK,L,True),"MySQL 8.0","既有 schema 相容、生態完整、Docker 官方映像穩定"],
       [("分析",INK,L,True),"Python 3.11 + Pandas","課程必要技術，向量化處理與資料聚合能力強"],
       [("視覺化",INK,L,True),"Matplotlib + Seaborn","課程必要技術，靜態圖品質佳、可嵌入 PHP"],
       [("機器學習",INK,L,True),"scikit-learn","RandomForest / IsolationForest / GridSearchCV 一站式"],
       [("最佳化",INK,L,True),"SciPy (HiGHS)","milp 整數規劃求解器，排班全域最佳化"],
       [("互動",INK,L,True),"Gradio","免前端即建分析儀表板，port 7860"],
       [("容器化",INK,L,True),"Docker Compose","單指令啟動三服務、跨平台一致性"],
       [("版控",INK,L,True),"Git / GitHub Actions","commit 規範 + 45 項自動化測試 CI"]],
      row_h=Inches(0.46), fsize=12.5)

# 2-3 Docker 一鍵部署
s = content_slide("系統架構 · 部署", "一行指令完成部署，並自動修復常見失敗點")
# terminal mock (light, professional)
tw=Inches(7.5); th=Inches(4.55); tx=ML; ty=Inches(2.05)
card(s, tx, ty, tw, th, fill=H("0F2233"), line=None, shadow=True, radius=0.03)
rect(s, tx, ty, tw, Inches(0.4), fill=H("17324A"))
for i,c in enumerate([H("E06C5E"),H("E6B450"),H("5BB98B")]):
    dot=s.shapes.add_shape(MSO_SHAPE.OVAL, tx+Inches(0.25+i*0.28), ty+Inches(0.13), Inches(0.14), Inches(0.14))
    dot.fill.solid(); dot.fill.fore_color.rgb=c; dot.line.fill.background()
text(s, tx+Inches(1.3), ty+Inches(0.07), Inches(5), Inches(0.28),
     [{'text':'bash · deploy','size':11,'color':H("8AA0B2"),'align':L}], font=FONT_M)
cmds=[("$ ",H("7FD0B0"),"git clone …/114-2_BigDataCC-2nd && cd docker"),
      ("$ ",H("7FD0B0"),"bash start_demo.sh"),
      ("",None,""),
      ("✓ ",H("E6B450"),"[1/5] 自動建立 .env（demo 預設密碼）"),
      ("✓ ",H("9FB4C4"),"[2/5] docker compose up --build -d"),
      ("✓ ",H("9FB4C4"),"[3/5] generate_mock_data.py  → 1,200 筆"),
      ("✓ ",H("9FB4C4"),"[4/5] fetch_sea_data.py      → 736 筆海象"),
      ("✓ ",H("9FB4C4"),"[5/5] analysis.py            → 25 張圖表"),
      ("",None,""),
      ("➜ ",H("7FD0B0"),"localhost:8080  PHP 系統"),
      ("➜ ",H("7FD0B0"),"localhost:7860  Gradio 分析")]
yy=ty+Inches(0.62)
for pre,col,c in cmds:
    if not c: yy+=Inches(0.18); continue
    text(s, tx+Inches(0.3), yy, tw-Inches(0.5), Inches(0.3),
         [{'text':pre,'size':12,'color':col or WHITE,'font':FONT_M},
          {'text':c,'size':12,'color':H("D5E0E8"),'font':FONT_M}], wrap=False)
    yy+=Inches(0.355)
# right notes
rx=ML+tw+Inches(0.4); rw=CW-tw-Inches(0.4)
notes=[("< 60 秒","完整啟動時間"),(".env 自動建立","修正學校轉移失敗主因"),
       ("WSL2 後端","Docker Desktop 跨平台"),("環境變數注入","帳密不入 repo")]
for i,(v,l) in enumerate(notes):
    y=Inches(2.05)+i*Inches(1.16)
    card(s, rx, y, rw, Inches(1.0), fill=WHITE, line=LINE, shadow=True)
    text(s, rx+Inches(0.22), y+Inches(0.13), rw-Inches(0.4), Inches(0.5),
         [{'text':v,'size':18,'color':GOLD,'bold':True}], font=FONT_M)
    text(s, rx+Inches(0.22), y+Inches(0.6), rw-Inches(0.4), Inches(0.3),
         [{'text':l,'size':11.5,'color':BODY}])

# 2-4 資料管線
s = content_slide("系統架構 · 資料管線", "從資料生成到決策呈現的單向流程")
fit_image(s, f"{FIG}/fig2_dataflow.png", ML, Inches(2.2), CW, Inches(3.4))
takeaway(s, "管線", "generate_mock_data → fetch_sea_data → analysis（清洗/統計/ML/排班）→ JSON+PNG → PHP & Gradio 雙呈現。")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 03  PHP
# ════════════════════════════════════════════════════════════════════════════
divider("03","PHP 應用系統","Web Application",
        ["12 項業務功能","三層級權限","登入 / 打卡 Demo","管理員儀表板 Demo"])

# 3-1 功能總覽
s = content_slide("PHP 系統 · 功能總覽", "完整業務系統，非僅展示用前端")
pages=[("login.php","登入 · Session 管理","全部",INK),
       ("punch.php","打卡 · 即時海象橫幅","全部",INK),
       ("records.php","個人值勤歷史查詢","全部",INK),
       ("leave.php","請假申請（假別/起訖）","全部",INK),
       ("admin_status.php","全員值勤總覽","管理員",INK2),
       ("admin_leave.php","請假審核","管理員",INK2),
       ("admin_users.php","帳號管理 / 停用","管理員",INK2),
       ("admin_export.php","值勤 CSV 匯出","管理員",INK2),
       ("scheduler.php","明日排班決策頁","管理員",GOLD),
       ("admin_dashboard.php","分析儀表板 + 25 圖","管理員",INK2),
       ("api_status.php","即時海況（60s 刷新）","全部",INK),
       ("reset_demo_pw.php","Demo 密碼重設","老闆",INK2)]
cw3=(CW-Inches(0.6))/3; chh=Inches(1.05)
for i,(fn,d,role,acc) in enumerate(pages):
    col=i%3; row=i//3
    x=ML+col*(cw3+Inches(0.3)); y=Inches(2.05)+row*(chh+Inches(0.18))
    star = acc==GOLD
    card(s, x, y, cw3, chh, fill=PANEL3 if star else WHITE, line=GOLD if star else LINE, shadow=True)
    rect(s, x, y, Inches(0.07), chh, fill=acc)
    text(s, x+Inches(0.22), y+Inches(0.12), cw3-Inches(0.4), Inches(0.3),
         [{'text':fn,'size':12.5,'color':acc if star else INK,'bold':True,'font':FONT_M}])
    text(s, x+Inches(0.22), y+Inches(0.48), cw3-Inches(0.4), Inches(0.3),
         [{'text':d,'size':11.5,'color':BODY}])
    text(s, x+Inches(0.22), y+Inches(0.75), cw3-Inches(0.4), Inches(0.26),
         [{'text':role,'size':10,'color':MUTED}])

# 3-2 Demo 登入/打卡
s = content_slide("PHP 系統 · Demo（一）", "員工端：登入動畫與即時海象打卡頁")
fit_image(s, f"{SCR}/01_login.png", ML, Inches(2.1), Inches(6.0), Inches(3.9), valign='t')
fit_image(s, f"{SCR}/02_dashboard.png", ML+Inches(6.3), Inches(2.1), Inches(6.0), Inches(3.9), valign='t')
text(s, ML, Inches(6.05), Inches(6.0), Inches(0.3),
     [{'text':'登入頁 · 粒子波動動畫背景','size':11.5,'color':MUTED,'align':C}])
text(s, ML+Inches(6.3), Inches(6.05), Inches(6.0), Inches(0.3),
     [{'text':'打卡頁 · 即時海象橫幅 + 個人疲勞卡','size':11.5,'color':MUTED,'align':C}])
takeaway(s, "測試帳號", "boss1 / admin1 / em1　·　Demo 密碼 demo1234（種子密碼於首次啟動以 bcrypt 重設）")

# 3-3 Demo 管理員儀表板
s = content_slide("PHP 系統 · Demo（二）", "管理員端：25 張圖表 + 互動地圖整合儀表板")
fit_image(s, f"{SCR}/03_dashboard.png", ML, Inches(2.05), Inches(8.0), Inches(4.85), valign='t')
rx=ML+Inches(8.3); rw=CW-Inches(8.3)
annotate(s, rx, Inches(2.05), rw,
         ["排班決策摘要（明日班表概覽）","Folium 互動海域地圖（可縮放點擊）",
          "25 張統計圖表嵌入呈現","點選任一圖可展開原圖",
          "每 60 秒自動刷新即時海象橫幅","響應式版面，行動裝置亦可瀏覽"],
         header_txt="儀表板內容")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 04  排班引擎（核心）
# ════════════════════════════════════════════════════════════════════════════
divider("04","核心：自動排班引擎","Automated Scheduling Engine",
        ["為何排班是核心差異","scheduler.php Demo","輸入 → 引擎 → 輸出",
         "五條決策規則","MILP 數學模型","最優性驗證","實機班表輸出"])

# 4-1 本系統四大核心差異化功能
s = content_slide("排班引擎 · 核心功能", "四項純海象資料系統無法產出的決策輸出")
feats=[
    ("自動排班班表","綜合海況風險、人員疲勞、外海暴露、船艦可用性四項因子，自動產出明日具名值勤班表。",GOLD),
    ("人員疲勞指數","連續值勤天數（60%）× 近 7 日累計工時（40%）合成 0–100 疲勞分，高疲勞者自動降低外海負荷。",INK),
    ("工時公平性 Gini","Lorenz 曲線量化人員工時分配均等度，Gini = 0.042，確保排班公平可追溯。",TEAL),
    ("船艦可用性管理","依累計趟次推估維護需求，可用度 < 30% 自動排除於排班候選池。",INK2),
]
for i,(t_,d,acc) in enumerate(feats):
    col=i%2; row=i//2
    x=ML+col*(Inches(6.2)+Inches(0.3)); y=Inches(2.1)+row*Inches(1.7)
    card(s, x, y, Inches(6.2), Inches(1.5), fill=WHITE, line=LINE)
    rect(s, x, y, Inches(0.08), Inches(1.5), fill=acc)
    text(s, x+Inches(0.28), y+Inches(0.18), Inches(5.7), Inches(0.38),
         [{'text':t_,'size':15,'color':INK,'bold':True}])
    text(s, x+Inches(0.28), y+Inches(0.62), Inches(5.7), Inches(0.8),
         [{'text':d,'size':12,'color':BODY}], leading=1.15)
takeaway(s, "整合", "四項功能共用同一個排班引擎，以 MILP 全域最佳化一次求解 — 不是分別看四張圖再人工判斷。")

# 4-2 scheduler.php Demo
s = content_slide("排班引擎 · Demo", "scheduler.php：海況機率自動產出明日班表")
fit_image(s, f"{SCR}/02_scheduler.png", ML, Inches(2.05), Inches(5.4), Inches(4.85), valign='t')
rx=ML+Inches(5.7); rw=CW-Inches(5.7)
annotate(s, rx, Inches(2.05), rw,
         [{'text':'頁頂 KPI：四項決策輸入','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 明日惡劣海況機率（ML %）","· 高疲勞人數","· 可用 / 維護中船艦數",
          {'text':'三欄班表：港口 · 近海 · 外海','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 每張人員卡：姓名 / 船艦 / 疲勞分 / 暴露%","· 附具體配置理由（可追溯）",
          {'text':'下方：輪休建議 + 船艦可用性','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 顯示 MILP 引擎與最優性差距"],
         header_txt="頁面資訊架構", size=12.5)

# 4-3 輸入→引擎→輸出 flow
s = content_slide("排班引擎 · 運作流程", "四項輸入經引擎整合，輸出可執行班表")
fit_image(s, f"{FIG}/fig3_engine.png", ML, Inches(2.1), CW, Inches(3.5))
takeaway(s, "整合", "海況、疲勞、暴露、船艦四訊號在引擎中被聯合最佳化 — 不是分別看四張圖，而是一次解出最優指派。")

# 4-4 五條決策規則
s = content_slide("排班引擎 · 決策規則", "五條規則編碼海事作業安全與公平原則")
rules=[("01","海況風險調控員額","明日惡劣機率 ≥ 50% → 外海僅留 1 人；< 25% → 外海最多 4 人。機率越高、外海員額越少。",INK),
       ("02","外海輪換公平","外海優先指派「疲勞低 AND 外海累積暴露低」者，兼顧安全與輪換公平。",INK),
       ("03","過勞者輕負荷","疲勞 ≥ 65（高）自動配置港口值守；人力充足且疲勞 ≥ 80 列入建議輪休。",INK),
       ("04","維護船艦排除","可用度 < 30% 標記需維護，不進入候選池；每艦僅一組人員。",INK),
       ("05","MILP 全域最佳化","scipy.optimize.milp（HiGHS）對人員×船艦矩陣求全域最優，ZONE_PRIORITY 確保安全關鍵海域優先填滿。",GOLD)]
for i,(n,t_,d,acc) in enumerate(rules):
    if i<4:
        col=i%2; row=i//2
        x=ML+col*(CW/2+Inches(0.1))-(Inches(0.0)); x=ML+col*(Inches(6.2)+Inches(0.3))
        y=Inches(2.1)+row*Inches(1.4); w=Inches(6.2); h=Inches(1.22)
    else:
        x=ML; y=Inches(4.9); w=CW; h=Inches(1.05)
    star=acc==GOLD
    card(s, x, y, w, h, fill=PANEL3 if star else WHITE, line=GOLD if star else LINE, shadow=True)
    text(s, x+Inches(0.2), y+Inches(0.12), Inches(0.9), Inches(0.6),
         [{'text':n,'size':26,'color':acc,'bold':True}], font=FONT_M)
    text(s, x+Inches(1.1), y+Inches(0.14), w-Inches(1.3), Inches(0.35),
         [{'text':t_,'size':14.5,'color':INK,'bold':True}])
    text(s, x+Inches(1.1), y+Inches(0.54), w-Inches(1.3), Inches(0.6),
         [{'text':d,'size':11.5,'color':BODY}], leading=1.12)

# 4-5 MILP 最佳化排班
s = content_slide("排班引擎 · 最佳化求解", "把排班問題交給數學求解器，找全域最優指派")
# three-step flow
steps=[
    ("輸入","人員清單（疲勞分、外海暴露率）\n可用船艦清單\n明日惡劣海況機率\n各海域可容員額",INK),
    ("求解器","Python scipy.optimize.milp\n目標：最小化綜合成本\n限制：每人一船、每船一組\n安全關鍵海域優先填滿",GOLD),
    ("輸出","具名人員×船艦指派矩陣\n三海域值勤班表\n輪休建議清單\n最優性驗證（差距 0%）",TEAL),
]
bw2=Inches(3.8); by2=Inches(2.2); bh2=Inches(3.8)
for i,(t_,d,acc) in enumerate(steps):
    x=ML+i*(bw2+Inches(0.45))
    card(s, x, by2, bw2, bh2, fill=WHITE, line=LINE)
    rect(s, x, by2, bw2, Inches(0.07), fill=acc)
    text(s, x+Inches(0.25), by2+Inches(0.25), bw2-Inches(0.5), Inches(0.44),
         [{'text':t_,'size':16,'color':acc,'bold':True}])
    hline(s, x+Inches(0.25), by2+Inches(0.77), bw2-Inches(0.5), color=LINE)
    paras=[{'text':ln,'size':12.5,'color':BODY,'bullet':'▪','bullet_color':acc,'space_after':8}
           for ln in d.split('\n')]
    text(s, x+Inches(0.25), by2+Inches(0.95), bw2-Inches(0.5), Inches(2.6), paras, leading=1.2)
    if i<2:
        text(s, x+bw2, by2, Inches(0.45), bh2,
             [{'text':'→','size':28,'color':GOLD,'bold':True,'align':C}], anchor='m')
takeaway(s, "效益", "MILP 將所有限制同時納入求解，不會因順序不同而得到不同班表 — 結果可重現、可驗證。")

# 4-6 最優性驗證
s = content_slide("排班引擎 · 最優性驗證", "MILP 證明貪婪法在此規模已達全域最優（差距 0%）")
fit_image(s, f"{IMG}/schedule_compare.png", ML, Inches(2.05), Inches(7.6), Inches(4.4), valign='t')
rx=ML+Inches(7.9); rw=CW-Inches(7.9)
for i,(v,l,acc) in enumerate([("215.6","MILP 指派成本",INK),("215.6","貪婪基準成本",INK2),("0.0%","最優性差距",TEAL)]):
    y=Inches(2.05)+i*Inches(1.0)
    kpi(s, rx, y, rw, Inches(0.86), v, l, accent=acc, value_size=24)
card(s, rx, Inches(5.15), rw, Inches(1.35), fill=PANEL, line=LINE)
text(s, rx+Inches(0.2), Inches(5.28), rw-Inches(0.4), Inches(1.1),
     [{'text':'學術誠實：','size':12.5,'color':GOLD,'bold':True,'space_after':3},
      {'text':'差距 0% 不是缺陷，而是「在 8 艦×12 人規模下貪婪法恰好已達全域最優」的數學驗證 — 這是有意義的正確結果。',
       'size':11.5,'color':BODY}], leading=1.15)

# 4-7 實機班表（LIVE）
rec=json.load(open(f"{IMG}/recommendations.json"))
sc=rec.get("schedule",{}); asg=sc.get("assignments",[])
s = content_slide("排班引擎 · 實機輸出", f"今日實際執行：明日（{sc.get('date','')}）惡劣海況 {sc.get('rough_prob',0)}% → 外海縮減至 1 人")
# KPI row
slots=sc.get("zone_slots",{})
for i,(v,l,acc) in enumerate([(str(sc.get('engine','milp')).upper(),"求解引擎",GOLD),
                              (f"{sc.get('cost_saving_pct',0)}%","最優性差距",TEAL),
                              (f"{rec.get('ml_rough_tomorrow',0)}%","ML 惡劣機率",TERRA),
                              (str(slots.get('外海',1)),"外海員額",INK)]):
    x=ML+i*(CW/4)
    kpi(s, x+Inches(0.05), Inches(2.0), CW/4-Inches(0.2), Inches(1.05), v, l, accent=acc, value_size=22)
# assignment table
zc={"外海":TERRA,"近海":INK2,"港口":TEAL}
rows=[]
for a in asg[:8]:
    rows.append([(a['zone'],zc.get(a['zone'],INK),L,True), a['name'], (a['vessel'],BODY,L,False,'m'),
                 (str(a['fatigue_score']),BODY,C), (f"{a['offshore_pct']}%",BODY,C), (a['reason'][:22],MUTED,L)])
table(s, ML, Inches(3.3),
      [Inches(1.3),Inches(2.0),Inches(2.0),Inches(1.3),Inches(1.7),Inches(3.633)],
      [("海域",L),("人員",L),("船艦",L),("疲勞",C),("外海暴露",C),("配置理由",L)],
      rows, row_h=Inches(0.4), fsize=11.5, hsize=12)
rest=[r['name'] for r in sc.get('rest_recommended',[])]
takeaway(s, "決策亮點", f"系統自動將最低暴露者派外海、把高疲勞的「{('、'.join(rest)) if rest else '—'}」列入輪休 — 一次完成安全與公平兩個目標。")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 05  資料工程
# ════════════════════════════════════════════════════════════════════════════
divider("05","資料工程","Data Engineering",
        ["Schema 設計與擴充","AR(1) 時序模擬模型","海域×海況機率設計","清洗與品質控管"])

# 5-1 Schema
s = content_slide("資料工程 · Schema", "在通用打卡表上擴充三個海事業務欄位")
lw=Inches(6.7)
card(s, ML, Inches(2.05), lw, Inches(4.5), fill=PANEL, line=LINE)
text(s, ML+Inches(0.3), Inches(2.2), lw-Inches(0.6), Inches(0.34),
     [{'text':'attendance 表（核心）','size':14,'color':INK,'bold':True}])
hline(s, ML+Inches(0.3), Inches(2.6), lw-Inches(0.6), color=LINE2)
cols=[("att_id","INT PK","流水號",False),("user_id","INT FK","值班人員",False),
      ("work_date","DATE","值班日期",False),("check_in","DATETIME","上勤 07–09h",False),
      ("check_out","DATETIME","下勤（依海況）",False),
      ("duty_zone","ENUM ←新增","港口/近海/外海",True),
      ("sea_state","ENUM ←新增","平靜/輕/中/大浪",True),
      ("vessel_id","VARCHAR ←新增","MAR-001~008",True)]
yy=Inches(2.75)
for c,t_,d,new in cols:
    text(s, ML+Inches(0.3), yy, Inches(2.0), Inches(0.3),
         [{'text':c,'size':12,'color':TEAL if new else INK,'bold':new,'font':FONT_M}])
    text(s, ML+Inches(2.4), yy, Inches(2.0), Inches(0.3),
         [{'text':t_,'size':11,'color':GOLD if new else MUTED,'font':FONT_M}])
    text(s, ML+Inches(4.5), yy, Inches(2.0), Inches(0.3),
         [{'text':d,'size':11,'color':BODY}])
    yy+=Inches(0.45)
rx=ML+lw+Inches(0.45); rw=CW-lw-Inches(0.45)
text(s, rx, Inches(2.05), rw, Inches(0.34),[{'text':'其他三張表','size':14,'color':INK,'bold':True}])
for i,(t_,cnt,d) in enumerate([("users","13 筆","三層級權限"),
                               ("leaves","60 筆","請假申請/審核"),
                               ("sea_observations","736 筆","CWA 浮標觀測（無金鑰自動模擬）")]):
    y=Inches(2.5)+i*Inches(1.3)
    card(s, rx, y, rw, Inches(1.1), fill=WHITE, line=LINE, shadow=True)
    text(s, rx+Inches(0.2), y+Inches(0.12), rw-Inches(0.4), Inches(0.34),
         [{'text':t_,'size':14,'color':TEAL,'bold':True,'font':FONT_M},
          {'text':'   '+cnt,'size':13,'color':GOLD,'bold':True}])
    text(s, rx+Inches(0.2), y+Inches(0.55), rw-Inches(0.4), Inches(0.45),
         [{'text':d,'size':11.5,'color':BODY}])

# 5-2 時序模擬設計
s = content_slide("資料工程 · 模擬模型", "海象具「持續性」：今天浪大、明天多半也大")
# two concept boxes
lw2=Inches(5.8)
card(s, ML, Inches(2.05), lw2, Inches(4.5), fill=PANEL, line=LINE)
text(s, ML+Inches(0.3), Inches(2.2), lw2-Inches(0.6), Inches(0.38),
     [{'text':'設計出發點：真實海象的時序特性','size':14,'color':INK,'bold':True}])
hline(s, ML+Inches(0.3), Inches(2.65), lw2-Inches(0.6), color=LINE2)
pts=[("天氣系統持續 3–7 天","今日大浪，明日通常也是大浪，不會突然平靜"),
     ("獨立隨機抽樣不夠","若每筆各自抽，海況沒有日際關聯，排班預測失去意義"),
     ("時序自相關模型","用前一日的海況嚴重度加上隨機擾動，生成下一日海況"),
     ("效果驗證","RandomForest 海況預測 AUC = 0.811（有時序訊號可學習）")]
yy=Inches(2.82)
for t_,d in pts:
    text(s, ML+Inches(0.3), yy, lw2-Inches(0.6), Inches(0.3),
         [{'text':'▪  '+t_,'size':13,'color':INK,'bold':True}])
    text(s, ML+Inches(0.55), yy+Inches(0.3), lw2-Inches(0.85), Inches(0.34),
         [{'text':d,'size':11.5,'color':BODY}])
    yy+=Inches(0.88)
rx=ML+lw2+Inches(0.45); rw=CW-lw2-Inches(0.45)
annotate(s, rx, Inches(2.05), rw,
         [{'text':'兩層機率設計','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "海域決定各海況基礎機率",
          "· 外海大浪基礎率 20%",
          "· 港口大浪基礎率  1%",
          {'text':'時序調整','size':13,'color':TEAL,'bold':True,'bullet':'▪','bullet_color':TEAL},
          "· 前日惡劣 → 今日惡劣機率升高",
          "· 生成 1,200 筆有時序結構的值勤紀錄",
          "· 讓後續 Markov、ML 預測有意義"],
         header_txt="機率結構", size=12.5)

# 5-3 機率設計
s = content_slide("資料工程 · 機率設計", "海域決定海況分布，海況決定工時")
table(s, ML, Inches(2.1),
      [Inches(2.2),Inches(2.0),Inches(2.0),Inches(2.0)],
      [("海況",L),("港口",C),("近海",C),("外海",C)],
      [[("平靜",INK,L,True),("70%",BODY,C),("40%",BODY,C),("15%",BODY,C)],
       [("輕浪",INK,L,True),("25%",BODY,C),("35%",BODY,C),("30%",BODY,C)],
       [("中浪",INK,L,True),("4%",BODY,C),("20%",BODY,C),("35%",BODY,C)],
       [("大浪",INK,L,True),("1%",MUTED,C),("5%",BODY,C),("20%",TERRA,C,True)]],
      row_h=Inches(0.55), fsize=13)
# right narrative
rx=ML+Inches(8.4); rw=CW-Inches(8.4)
annotate(s, rx, Inches(2.1), rw,
         ["海域出勤：港口 35% / 近海 40% / 外海 25%",
          "外海大浪機率 20%，是港口的 20 倍",
          "大浪天提前下勤 100 分鐘",
          "· 直接連動工時縮減效應",
          "上工時刻 07:00–09:00 隨機"],
         header_txt="設計邏輯", size=12.5)
takeaway(s, "閉環", "機率設計使「海域→海況→工時」三者環環相扣，後續 ANOVA、卡方、OLS 才能驗出顯著結構。")

# 5-4 清洗
s = content_slide("資料工程 · 清洗品質", "三步驟清洗，剔除率 < 1%")
steps=[("缺失值移除","dropna(check_in, check_out, duty_zone, sea_state, vessel_id)","確保分析關鍵欄位完整"),
       ("工時計算與過濾","hours = (check_out − check_in)/3600；保留 4 ≤ hours ≤ 14","剔除未完整打卡與異常長工時"),
       ("衍生欄位","month_str = work_date.strftime('%Y-%m')","供月度分組與時序分析")]
for i,(t_,code,d) in enumerate(steps):
    y=Inches(2.15)+i*Inches(1.4)
    card(s, ML, y, CW, Inches(1.2), fill=WHITE, line=LINE, shadow=True)
    rect(s, ML, y, Inches(1.0), Inches(1.2), fill=INK)
    text(s, ML, y, Inches(1.0), Inches(1.2),
         [{'text':str(i+1),'size':32,'color':WHITE,'bold':True,'align':C}], font=FONT_M, anchor='m')
    text(s, ML+Inches(1.25), y+Inches(0.14), CW-Inches(1.5), Inches(0.34),
         [{'text':t_,'size':14.5,'color':INK,'bold':True}])
    rect(s, ML+Inches(1.25), y+Inches(0.52), Inches(8.5), Inches(0.36), fill=PANEL2, rounded=True, radius=0.15)
    text(s, ML+Inches(1.4), y+Inches(0.52), Inches(8.3), Inches(0.36),
         [{'text':code,'size':11,'color':INK2,'font':FONT_M}], anchor='m')
    text(s, ML+Inches(10.0), y+Inches(0.5), CW-Inches(10.0)-Inches(0.1), Inches(0.5),
         [{'text':d,'size':11,'color':MUTED}], anchor='m', leading=1.05)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 06  統計分析
# ════════════════════════════════════════════════════════════════════════════
divider("06","統計分析","Statistical Analysis",
        ["檢定結果總覽","ANOVA · 海況→工時","卡方 · 海域×海況","OLS 多元迴歸","Spearman 相關矩陣"])

# 6-1 檢定總覽
s = content_slide("統計分析 · 總覽", "四項檢定，全部顯著（數值為實機輸出）")
kdata=[("F = 181.4","單因子 ANOVA","p < 0.0001 · 海況顯著影響工時",GOLD),
       ("χ² = 349.6","卡方獨立性","df=6 · 海域與海況顯著關聯",INK),
       ("R² = 0.784","OLS 多元迴歸","4 特徵解釋 78.4% 工時變異",TEAL),
       ("Gini = 0.042","工時公平性","近乎完全均等分配",TERRA)]
gw=(CW-Inches(0.9))/4
for i,(v,l,d,acc) in enumerate(kdata):
    x=ML+i*(gw+Inches(0.3))
    card(s, x, Inches(2.1), gw, Inches(2.5), fill=WHITE, line=LINE, shadow=True)
    rect(s, x, Inches(2.1), gw, Inches(0.07), fill=acc)
    text(s, x, Inches(2.5), gw, Inches(0.6),
         [{'text':v,'size':22,'color':INK,'bold':True,'align':C}], font=FONT_M)
    text(s, x+Inches(0.15), Inches(3.25), gw-Inches(0.3), Inches(0.34),
         [{'text':l,'size':13.5,'color':acc,'bold':True,'align':C}])
    text(s, x+Inches(0.2), Inches(3.7), gw-Inches(0.4), Inches(0.8),
         [{'text':d,'size':11,'color':BODY,'align':C}], leading=1.15)
# bottom interpretation
card(s, ML, Inches(4.95), CW, Inches(1.55), fill=PANEL, line=LINE)
text(s, ML+Inches(0.25), Inches(5.08), CW-Inches(0.5), Inches(0.34),
     [{'text':'統計意涵','size':13,'color':GOLD,'bold':True}])
text(s, ML+Inches(0.25), Inches(5.45), CW-Inches(0.5), Inches(1.0),
     [{'text':'大浪天工時較平靜天短約 1.5 小時（ANOVA）；外海大浪比例 20% vs 港口 1%（卡方）→ 排班引擎據此縮減外海員額；',
       'size':12.5,'color':BODY,'space_after':4},
      {'text':'工時受海況 / 海域 / 星期 / 打卡時刻共同決定，解釋力 78.4%，遠高於任何單維度模型。',
       'size':12.5,'color':BODY}], leading=1.2)

# 6-2 ANOVA + boxplot
s = content_slide("統計分析 · ANOVA", "海況等級越高，值勤工時越短（F = 181.4, p < 0.0001）")
fit_image(s, f"{IMG}/hours_boxplot.png", ML, Inches(2.05), Inches(7.6), Inches(4.4))
rx=ML+Inches(7.9); rw=CW-Inches(7.9)
annotate(s, rx, Inches(2.05), rw,
         ["H0：各海況平均工時相同","檢定量 F = 181.433","p 值 < 0.0001 → 拒絕 H0",
          "· 四組間至少一對顯著差異","大浪中位數較平靜低約 1.5h",
          "對應機制：大浪提前下勤 100 分","→ 數據驗證了模擬設計的因果"],
         header_txt="檢定說明", size=12.5)

# 6-3 卡方 + stacked
s = content_slide("統計分析 · 卡方檢定", "海域與海況並非獨立：外海明顯偏向惡劣海況")
fit_image(s, f"{IMG}/zone_sea_stacked.png", ML, Inches(2.05), Inches(7.2), Inches(4.4))
rx=ML+Inches(7.5); rw=CW-Inches(7.5)
annotate(s, rx, Inches(2.05), rw,
         ["H0：海域與海況彼此獨立","檢定量 χ² = 349.634，df = 6","p 值 < 0.0001 → 拒絕 H0",
          "外海大浪佔比 ≈ 20%","港口大浪佔比 ≈ 1%","· 海域分配直接決定風險暴露",
          "→ 排班引擎縮減外海員額的依據"],
         header_txt="檢定說明", size=12.5)

# 6-4 OLS
s = content_slide("統計分析 · OLS 迴歸", "上工時刻與海況是工時的兩大負向驅動因子")
fit_image(s, f"{IMG}/regression_coef.png", ML, Inches(2.05), Inches(7.4), Inches(4.4))
rx=ML+Inches(7.7); rw=CW-Inches(7.7)
annotate(s, rx, Inches(2.05), rw,
         ["標準化 OLS（numpy.linalg.lstsq）","R² = 0.784（解釋 78.4% 變異）",
          "上工時刻 β = −0.569（最強）","海況等級 β = −0.435（次強）",
          "海域距岸 β ≈ 0","星期 β = +0.014（可忽略）",
          "· β 已標準化，可直接比較重要性"],
         header_txt="模型結果", size=12.5)

# 6-5 Spearman
s = content_slide("統計分析 · 相關矩陣", "有序變數用 Spearman，揭示工時關聯結構")
fit_image(s, f"{IMG}/correlation_matrix.png", ML, Inches(2.05), Inches(5.6), Inches(4.4))
rx=ML+Inches(5.95); rw=CW-Inches(5.95)
annotate(s, rx, Inches(2.05), rw,
         ["海況為有序離散變數，Pearson 不適用","改用 Spearman 等級相關",
          {'text':'主要發現','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "工時 ↔ 上工時刻：r ≈ −0.52","工時 ↔ 海況等級：r ≈ −0.44",
          "海況 ↔ 海域：r ≈ +0.35","· 外海海況較惡劣的數值確認",
          "亦作為 OLS 特徵共線性診斷"],
         header_txt="方法與發現", size=12.5)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 07  預測與 ML
# ════════════════════════════════════════════════════════════════════════════
divider("07","預測與機器學習","Forecasting & Machine Learning",
        ["線性 + Holt 雙模型預測","RandomForest 海況分類","Markov 海況轉移","Isolation Forest 異常"])

# 7-1 預測雙模型
s = content_slide("預測 · 時間序列", "線性外推與 Holt 雙指數平滑並排對照")
fit_image(s, f"{IMG}/forecast_duty.png", ML, Inches(2.05), Inches(6.1), Inches(2.25), valign='t')
fit_image(s, f"{IMG}/forecast_holt.png", ML, Inches(4.35), Inches(6.1), Inches(2.25), valign='t')
rx=ML+Inches(6.4); rw=CW-Inches(6.4)
annotate(s, rx, Inches(2.05), rw,
         [{'text':'線性外推（上）','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 依趨勢線性延伸預測","· 含 95% 信賴區間帶",
          {'text':'Holt 雙指數平滑（下）','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 同時追蹤水準 + 趨勢分量","· 以純 NumPy 自行實作","· 對近期資料給予更高權重",
          {'text':'兩模型並排','size':13,'color':TEAL,'bold':True,'bullet':'▪','bullet_color':TEAL},
          "· 比較預測差異，增加可信度","· 趨勢方向一致即為穩健預測"],
         header_txt="兩種方法", size=12)

# 7-2 RandomForest
s = content_slide("機器學習 · RandomForest", "AUC = 0.811：用 TimeSeriesSplit 避免未來洩漏")
fit_image(s, f"{IMG}/feature_importance.png", ML, Inches(2.05), Inches(7.4), Inches(4.4))
rx=ML+Inches(7.7); rw=CW-Inches(7.7)
annotate(s, rx, Inches(2.05), rw,
         [{'text':'目標變數設計','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· mid_share = 當日中浪以上比例","· rough = (mid_share ≥ 0.35)","· 正例率 ~25%（原始僅 4%）",
          {'text':'訓練配置','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· GridSearchCV 超參數搜尋","· class_weight = balanced","· TimeSeriesSplit(5) 防未來洩漏",
          {'text':'結果','size':13,'color':TEAL,'bold':True,'bullet':'▪','bullet_color':TEAL},
          "· 測試集 acc 0.949 / AUC 0.811"],
         header_txt="ML 設計", size=12)

# 7-3 Markov
s = content_slide("預測 · Markov 轉移", "海況具狀態惰性，可外推未來 7 天惡劣機率")
fit_image(s, f"{IMG}/markov_heatmap.png", ML, Inches(2.1), CW, Inches(3.7))
takeaway(s, "預警", f"純 NumPy 矩陣連乘外推 7 天；本次大浪期望機率 {rec.get('markov_rough_7day',0)}%，超過 15% 即自動觸發排班預警。")

# 7-4 Isolation Forest
s = content_slide("異常偵測 · Isolation Forest", "單維 Z-score + 五維 Isolation Forest 互補偵測")
fit_image(s, f"{IMG}/anomaly_isoforest.png", ML, Inches(2.05), Inches(7.6), Inches(4.4))
rx=ML+Inches(7.9); rw=CW-Inches(7.9)
annotate(s, rx, Inches(2.05), rw,
         [{'text':'Z-score（工時單維）','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 工時超出 ±2σ 範圍","· 識別工時過長 / 過短的紀錄",
          {'text':'Isolation Forest（五維聯合）','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 同時考慮工時、海況、海域、","  打卡時刻、星期五個維度","· 偵測「情境型異常」",
          {'text':'互補效果','size':13,'color':TEAL,'bold':True,'bullet':'▪','bullet_color':TEAL},
          "· 兩法聯用：工時正常但情境異常","· 的紀錄，Z-score 看不到"],
         header_txt="兩法比較", size=12)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 08  人力資源決策
# ════════════════════════════════════════════════════════════════════════════
divider("08","人力資源決策","Workforce Decision Analytics",
        ["人員疲勞指數","工時公平性 Lorenz","船艦可用性","人員五維雷達圖"])

# 8-1 疲勞
s = content_slide("人資決策 · 疲勞指數", "連續值勤 × 近 7 日工時，量化過勞風險")
fit_image(s, f"{IMG}/fatigue.png", ML, Inches(2.05), Inches(7.6), Inches(4.4))
rx=ML+Inches(7.9); rw=CW-Inches(7.9)
annotate(s, rx, Inches(2.05), rw,
         [{'text':'合成公式','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 連續值勤天數 權重 60%","· 近 7 日累計工時 權重 40%","· 合成為 0–100 分",
          {'text':'分級','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· low < 40（綠）","· mid 40–65（橘）","· high ≥ 65（紅）→ 建議輪休",
          "高疲勞者由排班引擎自動避開高負荷"],
         header_txt="計算方式", size=12.5)

# 8-2 Lorenz
s = content_slide("人資決策 · 工時公平", "Gini = 0.042：工時分配近乎完全均等")
fit_image(s, f"{IMG}/fairness_lorenz.png", ML, Inches(2.05), Inches(6.0), Inches(4.4))
rx=ML+Inches(6.35); rw=CW-Inches(6.35)
annotate(s, rx, Inches(2.05), rw,
         ["Gini 係數移植自經濟學分配理論","0 = 完全平均，1 = 極度集中","本系統 Gini = 0.042 → 高度均等",
          "Lorenz 曲線緊貼對角線",
          {'text':'自動標記','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 過勞：工時 ≥ 中位數 ×1.3","· 閒置：工時 ≤ 中位數 ×0.7",
          "本次無人員達門檻 → 輪班執行均勻",
          "此維度純海象系統無法產出"],
         header_txt="Lorenz / Gini", size=12)

# 8-3 船艦
s = content_slide("人資決策 · 船艦可用性", "維護里程推估，需維護船艦自動排除於排班")
fit_image(s, f"{IMG}/vessel_availability.png", ML, Inches(2.05), Inches(7.6), Inches(4.4))
rx=ML+Inches(7.9); rw=CW-Inches(7.9)
annotate(s, rx, Inches(2.05), rw,
         ["可用度 = f(累計趟次 mod 45)","MAINT_INTERVAL = 45 趟","可用度 < 30% → 標記「需維護」",
          "需維護船艦不進入排班候選池","與疲勞 / 暴露聯動，避免高風險組合",
          "本次：所有船艦可用、無需維護"],
         header_txt="可用度模型", size=12.5)

# 8-4 雷達
s = content_slide("人資決策 · 人員雷達圖", "五維能力輪廓，支援精準調度決策")
fit_image(s, f"{IMG}/crew_radar.png", ML, Inches(2.05), Inches(6.4), Inches(4.4))
rx=ML+Inches(6.75); rw=CW-Inches(6.75)
annotate(s, rx, Inches(2.05), rw,
         ["五維：出勤次數 / 總工時 / 平均工時","　　　/ 外海暴露率 / 大浪暴露率","最大值歸一化，取前 6 名人員",
          {'text':'如何輔助排班','size':13,'color':INK,'bold':True,'bullet':'▪','bullet_color':GOLD},
          "· 外海+大浪暴露高 → 換至近海/港口","· 暴露低+疲勞低 → 外海最佳候選","· 總工時偏高 → 潛在過勞、建議輪休",
          "補足 Lorenz 只看整體分配的不足"],
         header_txt="維度與應用", size=12)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 09  互動與工程品質
# ════════════════════════════════════════════════════════════════════════════
divider("09","互動介面與工程品質","Interface & Engineering",
        ["Gradio 互動分析","Folium 互動地圖","GitHub 管理與 CI","技術清單與結語"])

# 9-1 Gradio
s = content_slide("互動介面 · Gradio", "篩選即時重跑 25 張圖表，七大分頁覆蓋全分析")
tabs=[("勤務決策建議","海況警示 · 海域風險 · 外海暴露 Top 8",TERRA),
      ("時序趨勢","月度趨勢 · 請假走勢 · 週幾出勤（3）",INK),
      ("預測與建模","線性 · Holt · 相關 · OLS · 特徵重要度（5）",GOLD),
      ("海域 × 海況","分布 · 堆疊 · 箱型 · 工時熱力（4）",TEAL),
      ("人力資源決策","疲勞 · Lorenz · 船艦 · 雷達 · 分群 · MILP（6）",GOLD),
      ("資源調度","船艦次數 · Pareto · 人員熱力（3）",INK),
      ("異常診斷","Z-score + Isolation Forest（2）",TERRA)]
for i,(t_,d,acc) in enumerate(tabs):
    col=i%2; row=i//2
    x=ML+col*(Inches(6.2)+Inches(0.3)); y=Inches(2.05)+row*Inches(0.98)
    w=Inches(6.2) if not(i==6) else CW
    card(s, x, y, w, Inches(0.82), fill=WHITE, line=LINE, shadow=True)
    rect(s, x, y, Inches(0.09), Inches(0.82), fill=acc)
    text(s, x+Inches(0.3), y+Inches(0.1), w-Inches(0.5), Inches(0.34),
         [{'text':t_,'size':14,'color':INK,'bold':True}])
    text(s, x+Inches(0.3), y+Inches(0.46), w-Inches(0.5), Inches(0.3),
         [{'text':d,'size':11,'color':MUTED}])
takeaway(s, "技術", "篩選在 SQL 層執行（不佔記憶體）；結果存 filtered_*，不覆蓋全覽，PHP 儀表板持續可用。")

# 9-2 Folium
s = content_slide("互動介面 · Folium 地圖", "三海域風險圈 + 船艦 + CWA 浮標站互動地圖")
fit_image(s, f"{IMG}/zone_map_static.png", ML, Inches(2.05), Inches(7.4), Inches(4.4))
rx=ML+Inches(7.7); rw=CW-Inches(7.7)
annotate(s, rx, Inches(2.05), rw,
         ["Folium（leaflet.js）輸出 duty_map.html","縮放 / 平移 / 點擊 popup 互動",
          "三海域半透明風險圈","點船艦標記：編號 / 海域 / 狀態","點浮標站：最新波高 / 海況",
          "靜態 PNG 內嵌 PHP，HTML 版以 iframe 呈現"],
         header_txt="地圖功能", size=12.5)

# 9-3 GitHub & CI
s = content_slide("工程品質 · GitHub & CI", "規範化 commit + 45 項自動化測試全綠")
table(s, ML, Inches(2.05),
      [Inches(1.7),Inches(6.3)],
      [("類型",L),("commit 說明",L)],
      [[("[docker]",INK2,L,True,'m'),"三容器 docker-compose 配置"],
       [("[app]",INK2,L,True,'m'),"PHP 系統 + 明日排班決策頁"],
       [("[data]",INK2,L,True,'m'),"模擬資料 + CWA 海象管線（AR(1)）"],
       [("[analysis]",GOLD,L,True,'m'),"排班 MILP + 25 圖 + ML + IsoForest + Holt"],
       [("[docs]",INK2,L,True,'m'),"期末報告 · 投影片 · stats_summary"],
       [("[fix]",INK2,L,True,'m'),"start_demo.sh 自動建 .env"]],
      row_h=Inches(0.55), fsize=12)
rx=ML+Inches(8.4); rw=CW-Inches(8.4)
card(s, rx, Inches(2.05), rw, Inches(4.45), fill=PANEL, line=LINE)
text(s, rx+Inches(0.25), Inches(2.2), rw-Inches(0.5), Inches(0.34),
     [{'text':'GitHub Actions CI','size':14,'color':INK,'bold':True}])
hline(s, rx+Inches(0.25), Inches(2.6), rw-Inches(0.5), color=LINE2)
ci=[("45 項測試","全數通過"),("MILP 排班","無雙重指派"),("Holt 預測","趨勢追蹤"),
    ("IsoForest","5% 污染率"),("ML CV","時序分割"),("25 圖表","全部生成")]
for i,(k,v) in enumerate(ci):
    y=Inches(2.78)+i*Inches(0.5)
    text(s, rx+Inches(0.25), y, Inches(2.0), Inches(0.34),[{'text':k,'size':12,'color':BODY}])
    text(s, rx+Inches(0.25), y, rw-Inches(0.5), Inches(0.34),
         [{'text':'✓ '+v,'size':12,'color':TEAL,'bold':True,'align':R}])
rect(s, rx+Inches(0.25), Inches(5.95), rw-Inches(0.5), Inches(0.42), fill=INK, rounded=True, radius=0.2)
text(s, rx+Inches(0.25), Inches(5.95), rw-Inches(0.5), Inches(0.42),
     [{'text':'45 passed in 17.87s','size':12,'color':WHITE,'bold':True,'align':C,'font':FONT_M}], anchor='m')

# 9-4 技術清單
s = content_slide("工程品質 · 技術清單", "必要 4／4 · 選擇性 7 · 差異化創新 4")
groups=[("必要技術 (4)",INK,[("Python + Pandas","清洗 / 統計 / 排班"),("Matplotlib / Seaborn","25 張圖表"),
                          ("Docker Compose","三容器一鍵部署"),("Git / GitHub","CI 45 tests")]),
        ("選擇性技術 (7)",INK2,[("MySQL 8.0","四張資料表"),("Apache + PHP","完整業務系統"),
                          ("scikit-learn","RF + IsoForest + GridSearch"),("Folium","互動海域地圖"),
                          ("Gradio","互動分析"),("CWA 開放資料","浮標海象"),("Jupyter","EDA 紀錄")]),
        ("差異化創新 (4)",GOLD,[("MILP (HiGHS)","排班全域最佳化"),("Isolation Forest","5 維異常偵測"),
                          ("Holt 平滑","純 NumPy 趨勢預測"),("人員雷達圖","五維調度輪廓")])]
gw=(CW-Inches(0.7))/3
for gi,(htxt,acc,items) in enumerate(groups):
    x=ML+gi*(gw+Inches(0.35))
    card(s, x, Inches(2.05), gw, Inches(4.5), fill=WHITE, line=LINE, shadow=True)
    rect(s, x, Inches(2.05), gw, Inches(0.5), fill=acc)
    text(s, x, Inches(2.05), gw, Inches(0.5),
         [{'text':htxt,'size':14,'color':WHITE,'bold':True,'align':C}], anchor='m')
    for i,(t_,d) in enumerate(items):
        y=Inches(2.72)+i*Inches(0.5)
        text(s, x+Inches(0.22), y, gw-Inches(0.4), Inches(0.3),
             [{'text':'✓ ','size':12,'color':acc,'bold':True},
              {'text':t_,'size':12.5,'color':INK,'bold':True}])
        text(s, x+Inches(0.55), y+Inches(0.24), gw-Inches(0.7), Inches(0.24),
             [{'text':d,'size':10,'color':MUTED}])

# 結語
s = slide()
rect(s, 0, 0, SW, Inches(0.1), fill=GOLD)
rect(s, 0, SH-Inches(0.1), SW, Inches(0.1), fill=GOLD)
rect(s, 0, 0, Inches(0.16), SH, fill=INK)
text(s, ML, Inches(0.55), CW, Inches(0.34),
     [{'text':'結語 · CONCLUSION','size':13,'color':GOLD,'bold':True}], font=FONT_M)
text(s, ML, Inches(0.9), CW, Inches(0.6),
     [{'text':'本學期達成','size':28,'color':INK,'bold':True}])
ach=["Docker 三容器一鍵部署，修正跨平台轉移問題（start_demo.sh 自動建 .env）",
     "MILP 整數規劃排班引擎 — 全域最優性差距 0%，全班唯一具名班表輸出",
     "RandomForest（acc 0.949 / AUC 0.811）+ Markov 雙模型海況預測",
     "Isolation Forest 5 維異常偵測，補強 Z-score 盲區",
     "Holt 雙指數平滑 + 線性外推雙趨勢預測（純 NumPy）",
     "人員雷達圖 · 疲勞指數 · Gini 0.042 · 船艦可用性四項人力決策",
     "25 張圖表 · 45 項 CI 全綠 · F=181.4 · χ²=349.6 · R²=0.784"]
for i,a in enumerate(ach):
    y=Inches(1.65)+i*Inches(0.6)
    rect(s, ML, y, CW, Inches(0.52), fill=PANEL if i%2==0 else WHITE, line=LINE, rounded=True, radius=0.08)
    text(s, ML+Inches(0.2), y, Inches(0.5), Inches(0.52),
         [{'text':'✓','size':16,'color':TEAL,'bold':True}], anchor='m')
    text(s, ML+Inches(0.7), y, CW-Inches(0.9), Inches(0.52),
         [{'text':a,'size':12.5,'color':INK}], anchor='m')
rect(s, ML, Inches(5.95), CW, Inches(0.5), fill=PANEL2, rounded=True, radius=0.1)
text(s, ML+Inches(0.2), Inches(5.95), CW-Inches(0.4), Inches(0.5),
     [{'text':'未來展望：CWA 即時 API · 多日滾動排班 · 行動裝置打卡推播','size':12.5,'color':INK2}], anchor='m')
rect(s, ML, Inches(6.6), CW, Inches(0.62), fill=INK, rounded=True, radius=0.1)
text(s, ML, Inches(6.6), CW, Inches(0.62),
     [{'text':'海象感知 × 人力資源 × 自動排班 — 從資料到決策的完整技術鏈','size':17,'color':WHITE,'bold':True,'align':C}], anchor='m')

OUT="/home/user/114-2_BigDataCC-2nd/docs/slides/第2組_海勤決策系統_期末簡報.pptx"
prs.save(OUT)
print(f"OK {len(prs.slides)} slides -> {OUT}")
