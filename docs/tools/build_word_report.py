# -*- coding: utf-8 -*-
"""
build_word_report.py — 產生期末報告正式 Word 檔（完全對齊老師範本格式）。

格式規範（依老師範本與示範報告 PDF）：
  封面：期末報告（粗體底線）＋題目＋校系＋組員＋指導老師
  章節：(一)摘要 (二)研究動機與研究問題 (三)文獻探討與回顧
        (四)研究方法與步驟 (五)研究結果(結論) (六)參考文獻
  字體：中文標楷體、英文 Times New Roman；本文 12pt、1.5 倍行距、首行縮排 2 字元
  引用：內文 [n] 編號對應參考文獻清單
執行：python3 docs/tools/build_word_report.py
"""
import json
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT    = Path(__file__).resolve().parents[2]
FIGDIR  = ROOT / "docs" / "figures"
CHARTS  = FIGDIR / "charts"
OUTNAME = "巨量資料與雲端運算技術_海勤人力資源與作業安全決策系統_黃宇平_傅瀚鋌_曾紹喆_劉家样_李翊丞_林秉賢.docx"
OUTPATH = ROOT / "docs" / OUTNAME

REC   = json.loads((FIGDIR / "recommendations.json").read_text(encoding="utf-8"))
STATS = json.loads((FIGDIR / "stats_summary.json").read_text(encoding="utf-8"))

EA_FONT, ASCII_FONT, MONO_FONT = "標楷體", "Times New Roman", "Consolas"


# ── 低階格式 helpers ──────────────────────────────────────────────────────────
def _set_run(run, size=12, bold=False, italic=False, underline=False,
             ea=EA_FONT, ascii_f=ASCII_FONT, color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.underline = underline
    run.font.name = ascii_f
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), ea)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def para(doc, text="", size=12, bold=False, align=None, indent_first=True,
         space_after=6, line=1.5, ea=EA_FONT, ascii_f=ASCII_FONT, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if align is not None:
        p.alignment = align
    if indent_first and text:
        pf.first_line_indent = Pt(size * 2)
    if text:
        _set_run(p.add_run(text), size=size, bold=bold, ea=ea, ascii_f=ascii_f, color=color)
    return p


def chapter(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.keep_with_next = True
    _set_run(p.add_run(text), size=18, bold=True)
    return p


def subhead(doc, text, size=14):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    _set_run(p.add_run(text), size=size, bold=True)
    return p


def numbered(doc, items, size=12):
    for i, t in enumerate(items, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Pt(28); pf.first_line_indent = Pt(-28)
        pf.space_after = Pt(4); pf.line_spacing = 1.5
        _set_run(p.add_run(f"({i}) "), size=size, bold=True)
        _set_run(p.add_run(t), size=size)


def cite_para(doc, segments, size=12, indent_first=True):
    """segments: list of (text, is_citation)；引用以上標 [n] 呈現。"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(6); pf.line_spacing = 1.5
    if indent_first:
        pf.first_line_indent = Pt(size * 2)
    for text, is_cite in segments:
        r = p.add_run(text)
        _set_run(r, size=size)
        if is_cite:
            r.font.superscript = False
    return p


def code_block(doc, lines):
    for ln in lines:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(0); pf.line_spacing = 1.15
        pf.left_indent = Pt(20)
        _set_run(p.add_run(ln), size=10, ea=MONO_FONT, ascii_f=MONO_FONT)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "F2F4F7")
        p._element.get_or_add_pPr().append(shd)
    para(doc, "", space_after=6, indent_first=False)


def figure(doc, path, caption, width_in=5.9):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width_in))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    _set_run(cap.add_run(caption), size=11, bold=True)


def style_cell(cell, text, size=11, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_after = Pt(2)
    _set_run(p.add_run(text), size=size, bold=bold)


def add_table(doc, headers, rows, caption=None, widths=None, size=11):
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(8)
        cp.paragraph_format.space_after = Pt(4)
        cp.paragraph_format.keep_with_next = True
        _set_run(cp.add_run(caption), size=11, bold=True)
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        style_cell(t.rows[0].cells[j], h, size=size, bold=True,
                   align=WD_ALIGN_PARAGRAPH.CENTER)
    for i, row in enumerate(rows, 1):
        for j, v in enumerate(row):
            style_cell(t.rows[i].cells[j], str(v), size=size)
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    para(doc, "", space_after=8, indent_first=False)
    return t


def add_page_number_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld_begin = OxmlElement("w:fldChar"); fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar"); fld_end.set(qn("w:fldCharType"), "end")
    run = p.add_run()
    run._element.append(fld_begin)
    run._element.append(instr)
    run._element.append(fld_end)
    _set_run(run, size=10)


# ── 文件主體 ──────────────────────────────────────────────────────────────────
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.54)
sec.left_margin = sec.right_margin = Cm(2.8)
sec.different_first_page_header_footer = True   # 封面不顯示頁碼
add_page_number_footer(sec)

# ===== 封面 =====
para(doc, "", space_after=40, indent_first=False)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_set_run(p.add_run("期末報告"), size=28, bold=True, underline=True)
p.paragraph_format.space_after = Pt(22)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_set_run(p.add_run("海勤人力資源與作業安全決策系統"), size=20, bold=True)
p.paragraph_format.space_after = Pt(6)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_set_run(p.add_run("—— 海象感知智慧排班・海事勤務雲端管理平台"), size=14)
p.paragraph_format.space_after = Pt(28)

for line, sz, sp in [("國立高雄科技大學", 16, 6), ("海事資訊科技系", 16, 30)]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_run(p.add_run(line), size=sz)
    p.paragraph_format.space_after = Pt(sp)

members = [
    ("組長", "黃宇平", "C112181108"),
    ("組員", "傅瀚鋌", "C112181112"),
    ("組員", "曾紹喆", "C112181182"),
    ("組員", "劉家样", "C111181141"),
    ("組員", "李翊丞", "C111181134"),
    ("組員", "林秉賢", "C112181148"),
]
for role, name, sid in members:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_run(p.add_run(f"{role}：{name}（{sid}）"), size=15)
    p.paragraph_format.space_after = Pt(8)

para(doc, "", space_after=14, indent_first=False)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_set_run(p.add_run("指導老師：張珀銀 老師"), size=15)
doc.add_page_break()

# ===== (一) 摘要 =====
chapter(doc, "(一)摘要")
para(doc, "本研究將上學期完成、僅能運行於 Windows XAMPP 之 PHP + MySQL 值勤管理雛形，"
          "改造為 Linux 雲端容器化之「海勤人力資源與作業安全決策系統」。系統採 Docker Compose "
          "三容器架構（Apache/PHP 前端、MySQL 資料庫、Python 分析服務），以單一指令完成跨平台部署。"
          "資料端以 Python 依輪班規則生成 1,200 筆含海域、海況、船艦欄位之六個月模擬值勤紀錄，"
          "並建立中央氣象署（CWA）浮標海象觀測管線（724 筆，無 API 金鑰時以季節性模型備援並誠實標記資料來源）。")
para(doc, "分析端以 Pandas 完成資料清洗與統計檢定：單因子 ANOVA 證實海況顯著影響工時"
          "（F = 167.9，p < 0.0001）、卡方檢定證實海域與海況顯著關聯（χ² = 331.0，p < 0.0001）、"
          "多元迴歸工時建模 R² = 0.778；並以 scikit-learn RandomForest 預測明日惡劣海況"
          "（測試集準確率 92.3%、AUC 0.713）。最終由自動排班引擎綜合海況風險、人員疲勞指數、"
          "外海暴露公平性（Gini = 0.033）與船艦可用性四項輸入，自動產出明日三海域具名值勤班表。"
          "成果以 21 張統計圖表、PHP 排班決策頁、Gradio 互動儀表板與 Folium 互動海域地圖呈現，"
          "全程以 GitHub 管理並通過 33 項自動化測試之 CI 驗證。本系統將海象由「視覺化對象」"
          "轉變為「人力決策輸入」，展示巨量資料與雲端運算技術於海事人力資源管理之實務應用。")

# ===== (二) 研究動機與研究問題 =====
chapter(doc, "(二)研究動機與研究問題")
subhead(doc, "研究動機：")
para(doc, "本組上學期完成之海事勤務值勤管理系統具備登入、打卡、請假與三層級權限功能，"
          "然其僅為「紀錄工具」而非「決策工具」。海勤值勤具高風險特性：海況惡劣時外海作業風險陡增，"
          "人員連續值勤造成之疲勞累積為海事事故重要肇因 [4]。管理者實務上最需要的不是更多報表，"
          "而是「明天該派誰、上哪艘船」的直接答案。同時，原系統綁定 Windows XAMPP，"
          "與雲端時代之部署型態脫節。本研究因此以容器化、資料分析與決策自動化三軸，"
          "將舊系統升級為決策支援系統（DSS）。")
subhead(doc, "研究問題：")
para(doc, "本研究所要解決之問題如下（量化）：", indent_first=False)
numbered(doc, [
    "原系統部署綁定 Windows + XAMPP，移轉至任一新主機須手動安裝設定 Apache、PHP、MySQL "
    "至少 3 套軟體，環境組態不可重現，遭遇異常時無法快速恢復服務。",
    "系統累積 1,200 筆值勤紀錄，卻產出 0 張分析圖表：管理層無法掌握工時負荷分布、"
    "海況與值勤量之關聯，更無任何預測能力。",
    "排班全憑人工經驗，未納入海況風險、人員疲勞、工時公平與船艦維護等至少 4 項決策因子，"
    "惡劣海況時段無法系統性縮減外海派遣員額。",
])
subhead(doc, "研究目的：")
para(doc, "對應上述問題，本研究設定三項量化目標：", indent_first=False)
numbered(doc, [
    "以 Docker Compose 建構 web、db、analysis 三容器架構，於 Linux 環境以單一指令"
    "（docker compose up）完成全系統部署，啟動時間 60 秒內，容器異常時可即時重建恢復服務。",
    "以 Pandas 清洗 1,200 筆值勤與 724 筆 CWA 浮標海象資料，產出 21 張涵蓋描述統計、"
    "假設檢定、時間序列預測、Markov 海況轉移與機器學習之分析圖表，並提供 Gradio 互動式儀表板。",
    "建立自動排班引擎 build_schedule()：綜合 RandomForest 明日海況預測、人員疲勞指數（0–100）、"
    "外海暴露公平輪換與船艦可用性共 4 項輸入，自動產出明日港口／近海／外海三海域具名班表，"
    "並附建議輪休與船艦維護清單。",
])

# ===== (三) 文獻探討與回顧 =====
chapter(doc, "(三)文獻探討與回顧")
subhead(doc, "容器化與可重現部署")
para(doc, "Merkel [1] 指出 Docker 以輕量級 Linux 容器封裝應用程式及其相依套件，"
          "使開發、測試與生產環境保持一致；容器可在數秒內啟動與停止，符合雲端動態調整資源之應用場景。"
          "Boettiger [2] 進一步論證容器化對「可重現運算」之價值——任何人在任何主機以相同映像即可"
          "重現相同服務。本研究據此以 Docker Compose 編排三容器，解決原系統綁定單一 Windows 主機、"
          "環境不可重現之問題。")
subhead(doc, "海勤人員疲勞與作業安全")
para(doc, "Smith 等人 [3] 之 Cardiff 海員疲勞研究計畫證實，連續值勤天數與不足之休息間隔"
          "顯著提高海上人為失誤風險；國際海事組織（IMO）[4] 之疲勞管理指引（MSC.1/Circ.1598）"
          "亦要求營運者以系統化方法監測與管理船員疲勞。本研究將「連續值勤天數」與「近 7 日累積工時」"
          "量化為 0–100 之疲勞指數，作為排班引擎之硬性輸入，呼應上述文獻對疲勞管理制度化之要求。")
subhead(doc, "海況統計建模與預測")
para(doc, "Monbet 等人 [5] 系統性回顧風與海況時間序列之隨機模型，其中 Markov 鏈為描述海況"
          "狀態轉移之經典方法。機器學習方面，Breiman [6] 提出之隨機森林（Random Forest）"
          "以多樹集成降低過度擬合，適合中小型結構化資料之分類任務。本研究同時採用兩者：以 Markov "
          "轉移矩陣估計未來 7 日海況分布，並以 scikit-learn [7] 之 RandomForest 結合滯後特徵"
          "預測明日是否出現惡劣海況，兩種方法互為驗證。")
subhead(doc, "工時公平性度量")
para(doc, "經濟學以 Lorenz 曲線與 Gini 係數衡量分配不均，Gini 係數介於 0（完全平等）至 1"
          "（完全不均）。本研究將其移植至工時分配場景：以各人員累積工時計算 Gini 係數並繪製 "
          "Lorenz 曲線，量化值勤負荷之公平程度，並以「外海暴露率」之相對排名驅動輪換建議，"
          "使排班公平性由主觀感受變為可監測指標。")
subhead(doc, "資料分析工具鏈")
para(doc, "本研究之分析管線建構於 Python 生態系：Pandas [8] 負責資料清洗與聚合，"
          "Matplotlib [9] 與 Seaborn 負責統計視覺化，Gradio [10] 提供無需前端開發即可部署之"
          "互動式機器學習介面，海象觀測資料則取自中央氣象署氣象資料開放平臺 [11]。")

# ===== (四) 研究方法與步驟 =====
chapter(doc, "(四)研究方法與步驟")
subhead(doc, "系統架構")
para(doc, "系統採三容器架構（圖 1）：web 容器（php:8.2-apache）承載 Linux 化改造後之 22 個 "
          "PHP 檔案，提供打卡、請假、權限管理與排班決策頁；db 容器（mysql:8.0）存放 users、"
          "attendance、leaves、sea_observations 四張資料表；analysis 容器（python:3.11）"
          "執行資料清洗、統計分析、機器學習與排班引擎。三容器共用 Docker 內部網路，"
          "分析產物（21 張 PNG、Folium 地圖、recommendations.json）經 named volume "
          "交付 PHP 前端嵌入顯示。")
figure(doc, FIGDIR / "fig1_architecture.png", "圖 1　三容器系統架構")

subhead(doc, "建置步驟說明")
para(doc, "A：使用 Docker 建置 MySQL 資料庫服務。以官方 mysql:8.0 映像啟動，連線帳密經"
          "環境變數（.env）注入而不寫死於程式碼。於上學期 attendance 表新增 duty_zone"
          "（港口/近海/外海）、sea_state（平靜/輕浪/中浪/大浪）、vessel_id 三個海事業務欄位，"
          "並新增 sea_observations 表存放 CWA 浮標逐日觀測。", indent_first=False)
para(doc, "B：使用 Docker 建置 Web 伺服器。以 php:8.2-apache 映像承載 PHP 系統，"
          "完成 Linux 化改造：路徑大小寫修正、字元集統一 utf8mb4、資料庫連線改以 getenv() "
          "讀取環境變數。新增 scheduler.php（明日排班決策頁）、api_status.php（每 60 秒輪詢之"
          "即時艦上狀態 JSON 端點）與管理員分析儀表板。", indent_first=False)
para(doc, "C：使用 Docker 建置 Python 分析服務。以 python:3.11 映像執行資料管線（圖 2）："
          "generate_mock_data.py 依輪班規則與海域—海況聯合機率生成 1,200 筆值勤紀錄；"
          "fetch_sea_data.py 擷取 CWA 開放資料浮標觀測（無 API 金鑰時自動以季節性模型模擬備援，"
          "欄位 data_source 誠實標記來源）；analysis.py 完成清洗、21 張圖表、RandomForest 訓練"
          "與排班計算；Gradio 於 7860 埠提供互動分析。", indent_first=False)
figure(doc, FIGDIR / "fig2_dataflow.png", "圖 2　資料流程：從資料生成到決策呈現", width_in=6.3)

subhead(doc, "資料清洗與品質控管")
para(doc, "清洗規則如下；本次執行 1,200 筆紀錄全數通過品質檢核（缺值與異常工時剔除率 0%，"
          "工時平均 9.02 小時、標準差 0.81）：")
code_block(doc, [
    'att = att.dropna(subset=["check_in","check_out","duty_zone","sea_state","vessel_id"])',
    'att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600',
    'att = att[(att["hours"] >= 4) & (att["hours"] <= 14)]   # 剔除異常工時',
])
para(doc, "海象資料品質方面，系統提供 CWA 浮標觀測與模擬海況之逐月對照圖（圖 3），"
          "驗證模擬資料之季節分布與真實海域特性一致，確保後續分析之效度。")
figure(doc, CHARTS / "sea_obs_comparison.png", "圖 3　CWA 浮標觀測與模擬海況之對照驗證", width_in=5.6)

subhead(doc, "統計分析與機器學習方法")
para(doc, "統計檢定採單因子變異數分析（ANOVA）檢驗海況對工時之影響、卡方獨立性檢定檢驗"
          "海域與海況之關聯，並以多元線性迴歸（OLS）建模工時驅動因子。預測建模包含："
          "（1）Markov 鏈海況轉移矩陣，估計未來 7 日惡劣海況機率；（2）RandomForest 二元分類器，"
          "以海況滯後特徵、星期、月份等特徵預測明日是否惡劣，以保留測試集（25%）之準確率與 "
          "AUC 評估；（3）K-means 人員值勤型態分群。公平性度量採 Gini 係數與 Lorenz 曲線。")

subhead(doc, "自動排班引擎")
para(doc, "核心函式 build_schedule()（圖 4）依四條規則運作：①明日惡劣海況機率越高，"
          "外海員額自動越少（機率 ≥ 50% 時外海僅留 1 組）；②外海優先指派「低疲勞且低外海暴露」"
          "人員，兼顧安全與公平輪換；③高疲勞（過勞）人員配置港口輕負荷或建議輪休；"
          "④維護中船艦自動排除，每艦同時段僅指派一組人員，可用船艦不足時輸出 vessel_limited "
          "警示。輸出統一寫入 recommendations.json，由 PHP 排班決策頁與 Gradio 雙端呈現。")
figure(doc, FIGDIR / "fig3_engine.png", "圖 4　自動排班決策引擎：四項輸入 → 決策規則 → 班表輸出", width_in=6.1)

subhead(doc, "版本控制與持續整合")
para(doc, "全程以 Git/GitHub 管理，commit 訊息依 [docker]、[app]、[data]、[analysis]、"
          "[docs]、[fix] 分類；GitHub Actions 於每次推送自動執行 33 項 pytest 測試，"
          "涵蓋資料清洗、統計函式、疲勞/公平性/船艦可用性計算與排班引擎行為驗證"
          "（如「不重複指派同艦」「過勞者不派外海」等決策約束）。")

subhead(doc, "作者貢獻")
add_table(
    doc,
    ["組員", "負責項目"],
    [
        ["黃宇平（組長）", "系統架構設計；Docker 三容器建置；PHP Linux 化（22 檔）；Schema 擴充；"
                          "模擬資料與 CWA 海象管線；Pandas 分析與 21 張圖表；RandomForest 與排班引擎；"
                          "Gradio 介面；CI 建置；整合測試；技術文件統籌"],
        ["傅瀚鋌", "海事業務知識（輪班制度、海域劃分）；資料欄位合理性審查；報告資料集章節初稿"],
        ["曾紹喆", "圖表洞察文字撰寫；投影片視覺設計與排版"],
        ["劉家样", "系統功能驗收測試（打卡、請假、管理介面邊界條件）；Demo 流程規劃與彩排"],
        ["李翊丞", "技術文件校對；參考文獻蒐集與格式整理"],
        ["林秉賢", "口頭報告稿件協調與時間掌控；Demo 現場操作；會議紀錄"],
    ],
    caption="表 1　組員分工表",
    widths=[3.4, 11.6],
)

# ===== (五) 研究結果(結論) =====
chapter(doc, "(五)研究結果(結論)")
para(doc, "本節逐條回應研究目的，所有數值皆為系統實際執行輸出。", indent_first=False)

subhead(doc, "1. 容器化部署結果")
para(doc, "系統於 Linux 環境以 docker compose up 單一指令完成三容器部署，實測約 60 秒內 "
          "web（:8080）與 Gradio（:7860）服務均可存取；容器異常時 docker compose restart "
          "數秒內恢復服務。環境組態完全由 docker-compose.yml 與 .env 描述，任意主機可重現，"
          "回應研究問題 (1)。")

subhead(doc, "2. 資料分析結果")
para(doc, "完成 1,200 筆值勤（2025-12-05 ～ 2026-06-06，12 位值勤人員、8 艘船艦）與 724 筆"
          "海象觀測之清洗與分析，產出 21 張統計圖表，回應研究問題 (2)。主要檢定與建模結果"
          "彙整如表 2：")
add_table(
    doc,
    ["分析項目", "統計量 / 指標", "結論"],
    [
        ["海況對工時影響（ANOVA）", "F = 167.9，p < 0.0001", "海況顯著影響工時，惡劣海況提前下勤"],
        ["海域×海況獨立性（卡方）", "χ² = 331.0（df = 6），p < 0.0001", "外海大浪比例顯著高於港口，符合海域特性"],
        ["工時驅動因子（OLS 迴歸）", "R² = 0.778", "上工時刻與海況等級為最大驅動因子"],
        ["明日惡劣海況預測（RandomForest）", "準確率 92.3%，AUC 0.713", "可作為排班引擎之風險輸入"],
        ["未來 7 日惡劣海況（Markov）", "機率 6.4%（明日 ML 預測 20.7%）", "兩模型互為驗證"],
        ["工時公平性（Gini 係數）", "Gini = 0.033", "分配均勻，輪班制度設計合理"],
    ],
    caption="表 2　統計檢定與建模結果摘要",
    widths=[5.0, 5.2, 4.8],
)
para(doc, "圖 5 顯示各海域之海況組成：外海大浪比例最高、港口以平靜為主，與卡方檢定結論一致。"
          "圖 6 之 Markov 轉移矩陣顯示海況具有顯著之狀態惰性（平靜後傾向持續平靜），"
          "為 7 日預測提供依據。圖 7 為 RandomForest 特徵重要度，海況滯後特徵（昨日海況）"
          "貢獻最大，符合海象時間連續性之物理直覺。")
figure(doc, CHARTS / "zone_sea_stacked.png", "圖 5　各海域海況組成（與卡方檢定 χ² = 331.0 相互印證）", width_in=5.6)
figure(doc, CHARTS / "markov_heatmap.png", "圖 6　Markov 海況轉移矩陣與 7 日惡劣海況機率", width_in=5.6)
figure(doc, CHARTS / "feature_importance.png", "圖 7　RandomForest 特徵重要度（測試集準確率 92.3%、AUC 0.713）", width_in=5.6)

subhead(doc, "3. 人力資源決策與自動排班結果")
para(doc, "此部分為本系統與純海象視覺化系統之結構性差異——以下產出皆需人員/勤務/船艦資料，"
          "純海象資料無法產生。圖 8 為人員疲勞指數排行（連續值勤天數＋近 7 日工時），"
          "圖 9 之 Lorenz 曲線顯示工時分配貼近完全平等線（Gini = 0.033），"
          "圖 10 為船艦可用性與維護里程（MAR-007 達維護門檻，排班自動排除）。")
figure(doc, CHARTS / "fatigue.png", "圖 8　人員疲勞指數排行（0–100，紅色為高疲勞建議輪休）", width_in=5.6)
figure(doc, CHARTS / "fairness_lorenz.png", "圖 9　工時公平性 Lorenz 曲線（Gini = 0.033，分配均勻）", width_in=5.4)
figure(doc, CHARTS / "vessel_availability.png", "圖 10　船艦可用性與維護里程", width_in=5.6)

sch = REC.get("schedule", {})
rows = [[a["zone"], a["name"], a["vessel"], a["fatigue_score"],
         f"{a['offshore_pct']}%", a["reason"]] for a in sch.get("assignments", [])]
para(doc, f"排班引擎以明日惡劣海況機率 {sch.get('rough_prob')}% 為輸入，"
          f"自動決定三海域員額（港口 {sch.get('zone_slots',{}).get('港口')}、"
          f"近海 {sch.get('zone_slots',{}).get('近海')}、外海 {sch.get('zone_slots',{}).get('外海')} 人），"
          f"並產出具名班表（表 3）。維護中船艦 {', '.join(sch.get('maintenance_vessels', []) or ['無'])} "
          "已自動排除於指派之外，回應研究問題 (3)。")
add_table(
    doc,
    ["海域", "人員", "船艦", "疲勞指數", "外海暴露", "指派理由"],
    rows,
    caption=f"表 3　自動排班引擎輸出之明日班表（{sch.get('date','')}，系統實際輸出）",
    widths=[1.6, 2.0, 2.2, 1.9, 1.9, 5.4],
)
figure(doc, CHARTS / "zone_map_static.png", "圖 11　三海域風險地圖（另提供 Folium 互動版 duty_map.html）", width_in=5.8)

subhead(doc, "4. 結論與未來展望")
para(doc, "本研究完成由「值勤紀錄工具」至「人力資源決策系統」之升級：海象在本系統中僅為"
          "輸入訊號，真正輸出為人員疲勞、工時公平、船艦可用性與自動產生之明日班表——"
          "此為純海象視覺化系統無法產出之決策維度。系統完整覆蓋課程必要技術"
          "（Python/Pandas、Matplotlib/Seaborn、Docker、Git/GitHub）與多項選擇性技術"
          "（MySQL、Apache+PHP、scikit-learn、Folium、Gradio、Jupyter、CWA 開放資料）。")
para(doc, "未來可延伸方向如下：", indent_first=False)
numbered(doc, [
    "接入 CWA 即時 API 金鑰以取得線上觀測資料（金鑰備援機制已內建，僅需填入 .env）。",
    "以線性規劃／整數規劃將排班引擎由啟發式規則升級為最佳化求解，並支援多日滾動排班。",
    "開發行動裝置現場打卡與推播通知，將明日班表直接送達值勤人員。",
])

# ===== (六) 參考文獻 =====
chapter(doc, "(六)參考文獻")
refs = [
    "D. Merkel, Docker: Lightweight Linux containers for consistent development and deployment. Linux Journal, 2014, 2014(239).",
    "C. Boettiger, An introduction to Docker for reproducible research. ACM SIGOPS Operating Systems Review, 2015, 49(1), 71-79.",
    "A. Smith; P. Allen, and E. Wadsworth, Seafarer fatigue: The Cardiff Research Programme. Cardiff University, 2006.",
    "International Maritime Organization, Guidelines on fatigue (MSC.1/Circ.1598). IMO, 2019.",
    "V. Monbet; P. Ailliot, and M. Prevosto, Survey of stochastic models for wind and sea state time series. Probabilistic Engineering Mechanics, 2007, 22(2), 113-126.",
    "L. Breiman, Random forests. Machine Learning, 2001, 45(1), 5-32.",
    "F. Pedregosa, et al., Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 2011, 12, 2825-2830.",
    "W. McKinney, “Data structures for statistical computing in Python,” in Proceedings of the 9th Python in Science Conference, 2010; pp. 56-61.",
    "J. D. Hunter, Matplotlib: A 2D graphics environment. Computing in Science & Engineering, 2007, 9(3), 90-95.",
    "A. Abid; A. Abdalla; A. Abid; D. Khan; A. Alfozan, and J. Zou, Gradio: Hassle-free sharing and testing of ML models in the wild. 2019, arXiv:1906.02569.",
    "中央氣象署，氣象資料開放平臺。https://opendata.cwa.gov.tw（擷取日期：2026 年 6 月）.",
]
for i, ref in enumerate(refs, 1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Pt(24); pf.first_line_indent = Pt(-24)
    pf.space_after = Pt(4); pf.line_spacing = 1.3
    _set_run(p.add_run(f"{i}. "), size=11)
    _set_run(p.add_run(ref), size=11)

doc.save(str(OUTPATH))
print(f"saved: {OUTPATH}")
print(f"size: {OUTPATH.stat().st_size/1024:.0f} KB")
