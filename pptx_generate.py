"""
Zamonaviy PPTX generatori (opsiyalar bilan).

Imkoniyatlar:
  - 16:9 format, 3 ta rang mavzusi (ocean / emerald / sunset).
  - Foydalanuvchi tanlovi (options dict orqali):
        images      -> slaydlarga mavzuga mos rasm (Pexels) qo'shish
        icons       -> har slayd sarlavhasi yoniga mos emoji-ikona
        chart_type  -> grafik turi: column | bar | pie | line | None (grafiksiz)
        chart_count -> nechta grafik slaydi (1..3)
  - Aqlli grafik ma'lumoti Gemini orqali olinadi.

Tashqi shablonga bog'liq emas — har bir element qo'lda chiziladi.
"""

import os
import uuid
import random

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.chart.data import CategoryChartData

from ai_service import GeminiService

try:
    from PIL import Image
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False


# ---------------------------------------------------------------------------
# Rang mavzulari
# ---------------------------------------------------------------------------
THEMES = {
    "ocean": {
        "name": "Okean (ko'k)",
        "primary": RGBColor(0x12, 0x2A, 0x4A),
        "accent":  RGBColor(0x3B, 0x82, 0xF6),
        "accent2": RGBColor(0x60, 0xA5, 0xFA),
        "text":    RGBColor(0x1F, 0x2A, 0x37),
        "muted":   RGBColor(0x6B, 0x72, 0x80),
        "light":   RGBColor(0xEF, 0xF4, 0xFB),
        "on_dark": RGBColor(0xFF, 0xFF, 0xFF),
    },
    "emerald": {
        "name": "Zumrad (yashil)",
        "primary": RGBColor(0x0B, 0x3D, 0x2E),
        "accent":  RGBColor(0x10, 0xB9, 0x81),
        "accent2": RGBColor(0x34, 0xD3, 0x99),
        "text":    RGBColor(0x18, 0x2A, 0x24),
        "muted":   RGBColor(0x6B, 0x72, 0x80),
        "light":   RGBColor(0xEC, 0xFD, 0xF5),
        "on_dark": RGBColor(0xFF, 0xFF, 0xFF),
    },
    "sunset": {
        "name": "Shafaq (binafsha-marjon)",
        "primary": RGBColor(0x3B, 0x12, 0x3A),
        "accent":  RGBColor(0xF9, 0x73, 0x16),
        "accent2": RGBColor(0xFB, 0x92, 0x3C),
        "text":    RGBColor(0x2A, 0x18, 0x29),
        "muted":   RGBColor(0x6B, 0x72, 0x80),
        "light":   RGBColor(0xFD, 0xF2, 0xF8),
        "on_dark": RGBColor(0xFF, 0xFF, 0xFF),
    },
}

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Grafik turi xaritasi
CHART_TYPE_MAP = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar":    XL_CHART_TYPE.BAR_CLUSTERED,
    "pie":    XL_CHART_TYPE.PIE,
    "line":   XL_CHART_TYPE.LINE_MARKERS,
}

# Sarlavha kalit so'zlari -> emoji ikona (o'zbekcha/inglizcha)
ICON_MAP = [
    (("kirish", "introduction", "muqaddima"), "📖"),
    (("xulosa", "conclusion", "yakun"), "✅"),
    (("tarix", "history", "kelib chiq"), "🏛️"),
    (("ta'rif", "tushuncha", "concept", "asosiy"), "💡"),
    (("texnologi", "technology", "tizim", "system"), "⚙️"),
    (("afzal", "advantage", "benefit", "foyda"), "⭐"),
    (("muammo", "problem", "challenge", "kamchilik"), "⚠️"),
    (("statistik", "statistics", "raqam", "ko'rsatkich", "data", "ma'lumot"), "📊"),
    (("kelajak", "future", "istiqbol", "rivoj"), "🚀"),
    (("ta'lim", "education", "o'qit", "maktab", "school"), "🎓"),
    (("iqtisod", "economy", "moliya", "finance", "pul"), "💰"),
    (("sog'liq", "health", "tibbiyot", "medicine"), "🏥"),
    (("tabiat", "ekologi", "nature", "environment", "atrof"), "🌿"),
    (("aloqa", "communication", "internet", "tarmoq", "network"), "🌐"),
    (("qo'llan", "application", "amaliy", "usage", "foydalanish"), "🛠️"),
    (("maqsad", "goal", "vazifa", "objective"), "🎯"),
]


# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------
def _blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _fill_background(slide, color):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def _add_rect(slide, left, top, width, height, color, shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, left, top, width, height)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def _add_text(slide, left, top, width, height, text, size, color,
              bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
              font="Calibri", italic=False, wrap=True):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.name = font
    f.color.rgb = color
    return box, tf


def _clean_bullets(raw):
    lines = []
    for line in (raw or "").split("\n"):
        s = line.strip()
        if not s:
            continue
        s = s.lstrip("*-•▸●○◦·> ").strip().replace("**", "").strip()
        if s:
            lines.append(s)
    return lines


def _shorten(text, limit):
    """Juda uzun matnni so'z chegarasida qisqartiradi."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:.")
    return cut + "…"


def _pick_icon(title):
    t = (title or "").lower()
    for keys, emoji in ICON_MAP:
        if any(k in t for k in keys):
            return emoji
    return "📌"


def _add_image_fit(slide, path, box_l, box_t, box_w, box_h):
    """Rasmni berilgan quti ichiga nisbatini saqlagan holda joylashtiradi (markazda)."""
    try:
        ratio = None
        if _HAS_PIL:
            with Image.open(path) as im:
                iw, ih = im.size
                if iw and ih:
                    ratio = iw / ih
        if ratio is None:
            ratio = box_w / box_h

        box_ratio = box_w / box_h
        if ratio > box_ratio:
            # rasm kengroq -> kenglik bo'yicha cheklaymiz
            w = box_w
            h = int(box_w / ratio)
        else:
            h = box_h
            w = int(box_h * ratio)
        left = box_l + (box_w - w) // 2
        top = box_t + (box_h - h) // 2
        slide.shapes.add_picture(path, left, top, width=w, height=h)
        return True
    except Exception as e:
        print(f"⚠️ Rasm joylashda xato: {e}")
        return False


def _add_footer(slide, theme, index, total, topic):
    _add_rect(slide, Inches(0.9), Inches(6.95), Inches(11.53), Inches(0.02), theme["light"])
    _add_text(slide, Inches(0.9), Inches(7.0), Inches(9.0), Inches(0.4),
              (topic or "")[:60], 10, theme["muted"], align=PP_ALIGN.LEFT)
    _add_text(slide, Inches(11.0), Inches(7.0), Inches(1.43), Inches(0.4),
              f"{index} / {total}", 10, theme["muted"], align=PP_ALIGN.RIGHT)


def _slide_header(slide, theme, title, icons=False):
    """Sarlavha bloki (ixtiyoriy ikona bilan). Sarlavha matnining chap chetini qaytaradi."""
    _add_rect(slide, Inches(0.9), Inches(0.62), Inches(0.18), Inches(0.7), theme["accent"])
    title_left = Inches(1.25)
    if icons:
        emoji = _pick_icon(title)
        # Segoe UI Emoji — Windows/PowerPoint'da rangli emoji to'g'ri ko'rinishi uchun
        _add_text(slide, Inches(1.25), Inches(0.45), Inches(0.9), Inches(1.0),
                  emoji, 28, theme["primary"], anchor=MSO_ANCHOR.MIDDLE,
                  font="Segoe UI Emoji")
        title_left = Inches(2.1)
    _add_text(slide, title_left, Inches(0.5), Inches(10.5), Inches(1.0),
              title, 28, theme["primary"], bold=True,
              align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
    _add_rect(slide, Inches(0.9), Inches(1.55), Inches(11.53), Inches(0.03), theme["light"])


# ---------------------------------------------------------------------------
# Slayd qoliplari
# ---------------------------------------------------------------------------
def _build_title_slide(prs, theme, d):
    slide = _blank_slide(prs)
    _fill_background(slide, theme["primary"])
    _add_rect(slide, Inches(0), Inches(0), Inches(0.28), SLIDE_H, theme["accent"])
    _add_rect(slide, Inches(11.2), Inches(0), Inches(2.13), Inches(2.2), theme["accent"])
    _add_rect(slide, Inches(10.4), Inches(0), Inches(0.7), Inches(1.3), theme["accent2"])

    uni = d.get("university_name") or d.get("uni_kafedra", "")
    kaf = d.get("uni_kafedra", "")
    _add_text(slide, Inches(0.9), Inches(0.9), Inches(9.5), Inches(0.9),
              str(uni).upper(), 16, theme["on_dark"], bold=True)
    if kaf and kaf != uni:
        _add_text(slide, Inches(0.9), Inches(1.55), Inches(9.5), Inches(0.6),
                  str(kaf), 13, theme["accent2"])
    _add_text(slide, Inches(0.9), Inches(2.7), Inches(11.0), Inches(2.2),
              d.get("topic", "Mavzu"), 40, theme["on_dark"], bold=True,
              anchor=MSO_ANCHOR.MIDDLE)
    _add_rect(slide, Inches(0.95), Inches(4.95), Inches(2.6), Inches(0.08), theme["accent"])

    info = [
        f"Bajardi:  {d.get('student_fio', '')}",
        f"Guruh:  {d.get('student_group', '')}",
        f"Yil:  {d.get('year', '')}",
    ]
    box = slide.shapes.add_textbox(Inches(0.9), Inches(5.6), Inches(7.0), Inches(1.5))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(info):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = line
        run.font.size = Pt(15)
        run.font.name = "Calibri"
        run.font.color.rgb = theme["on_dark"]
        p.space_after = Pt(2)
    return slide


def _build_content_slide(prs, theme, title, bullets, index, total, topic,
                         image_path=None, icons=False):
    slide = _blank_slide(prs)
    _fill_background(slide, RGBColor(0xFF, 0xFF, 0xFF))
    _slide_header(slide, theme, title, icons=icons)

    has_image = bool(image_path) and os.path.exists(image_path or "")

    if has_image:
        text_w = Inches(6.5)
        max_bullets = 4
        base_size = 15
    else:
        text_w = Inches(11.3)
        max_bullets = 6
        base_size = 16

    box = slide.shapes.add_textbox(Inches(1.0), Inches(1.9), text_w, Inches(4.95))
    tf = box.text_frame
    tf.word_wrap = True
    # Matn quti balandligidan oshib ketsa — avtomatik kichraytiriladi (slaydga sig'adi)
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

    if not bullets:
        bullets = ["Ma'lumot generatsiya qilinmadi."]
    bullets = bullets[:max_bullets]

    # Punktlar ko'p bo'lsa shriftni biroz kichraytiramiz (qo'shimcha xavfsizlik)
    if len(bullets) >= 5:
        base_size -= 1

    for i, line in enumerate(bullets):
        # Juda uzun punktni qisqartiramiz (sig'masligi oldini olish uchun)
        line = _shorten(line, 220)
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(8)
        p.line_spacing = 1.05
        m = p.add_run()
        m.text = "▸  "
        m.font.size = Pt(base_size)
        m.font.bold = True
        m.font.name = "Calibri"
        m.font.color.rgb = theme["accent"]
        t = p.add_run()
        t.text = line
        t.font.size = Pt(base_size)
        t.font.name = "Calibri"
        t.font.color.rgb = theme["text"]

    if has_image:
        # O'ng tomonda rasm uchun joy + nozik ramka effekti
        frame_l, frame_t = Inches(7.75), Inches(1.95)
        frame_w, frame_h = Inches(4.6), Inches(4.5)
        _add_rect(slide, frame_l - Inches(0.06), frame_t - Inches(0.06),
                  frame_w + Inches(0.12), frame_h + Inches(0.12), theme["light"])
        _add_image_fit(slide, image_path, frame_l, frame_t, frame_w, frame_h)

    _add_footer(slide, theme, index, total, topic)
    return slide


def _build_chart_slide(prs, theme, cd, index, total, topic, chart_type="column"):
    slide = _blank_slide(prs)
    _fill_background(slide, RGBColor(0xFF, 0xFF, 0xFF))
    _slide_header(slide, theme, cd.get("title") or "Statistik ko'rsatkichlar", icons=False)

    xl_type = CHART_TYPE_MAP.get(chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)

    chart_data = CategoryChartData()
    chart_data.categories = cd["categories"]
    if xl_type == XL_CHART_TYPE.PIE:
        # Doiraviy grafik faqat bitta seriyani ko'rsatadi
        first = cd["series"][0]
        chart_data.add_series(first["name"], first["values"])
    else:
        for series in cd["series"]:
            chart_data.add_series(series["name"], series["values"])

    gframe = slide.shapes.add_chart(
        xl_type, Inches(1.2), Inches(1.95), Inches(10.9), Inches(4.8), chart_data
    )
    chart = gframe.chart
    chart.has_title = False

    if xl_type == XL_CHART_TYPE.PIE:
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.RIGHT
        chart.legend.include_in_layout = False
        try:
            points = chart.plots[0].series[0].points
            palette = [theme["accent"], theme["accent2"], theme["primary"],
                       theme["muted"], RGBColor(0x93, 0xC5, 0xFD)]
            for i, point in enumerate(points):
                point.format.fill.solid()
                point.format.fill.fore_color.rgb = palette[i % len(palette)]
        except Exception:
            pass
    else:
        chart.has_legend = len(cd["series"]) > 1
        if chart.has_legend:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
        try:
            palette = [theme["accent"], theme["accent2"], theme["primary"]]
            for si, plot_series in enumerate(chart.series):
                plot_series.format.fill.solid()
                plot_series.format.fill.fore_color.rgb = palette[si % len(palette)]
        except Exception:
            pass

    _add_footer(slide, theme, index, total, topic)
    return slide


def _build_closing_slide(prs, theme, d):
    slide = _blank_slide(prs)
    _fill_background(slide, theme["primary"])
    _add_rect(slide, Inches(0), Inches(0), Inches(0.28), SLIDE_H, theme["accent"])
    _add_text(slide, Inches(0.9), Inches(2.7), Inches(11.5), Inches(1.6),
              "E'tiboringiz uchun rahmat!", 44, theme["on_dark"], bold=True,
              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    _add_rect(slide, Inches(5.86), Inches(4.4), Inches(1.6), Inches(0.08), theme["accent"])
    _add_text(slide, Inches(0.9), Inches(4.7), Inches(11.5), Inches(0.8),
              str(d.get("student_fio", "")), 18, theme["accent2"], align=PP_ALIGN.CENTER)
    return slide


# ---------------------------------------------------------------------------
# Asosiy funksiya
# ---------------------------------------------------------------------------
async def generate_pptx_file(doc_data, presentation_content, temp_dir,
                             theme_name=None, options=None, theme_path=None):
    """
    Zamonaviy prezentatsiya yaratadi.

    presentation_content: [{"title": str, "content": str, "image": str|None}]
    options: {
        "images": bool,
        "icons": bool,
        "chart_type": "column"|"bar"|"pie"|"line"|None,
        "chart_count": int,
    }
    """
    options = options or {}
    use_icons = bool(options.get("icons"))
    chart_type = options.get("chart_type")
    chart_count = int(options.get("chart_count") or 0)
    if not chart_type:
        chart_count = 0

    if theme_name not in THEMES:
        theme_name = random.choice(list(THEMES.keys()))
    theme = THEMES[theme_name]

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    topic = doc_data.get("topic", "Mavzu")

    # Titul slayd
    _build_title_slide(prs, theme, doc_data)

    # Grafik ma'lumotlarini olish (chart_count ta)
    chart_dicts = []
    if chart_count > 0:
        try:
            gemini = GeminiService()
            for _ in range(chart_count):
                data = await gemini.generate_chart_data(topic)
                if data and data.get("categories") and data.get("series"):
                    chart_dicts.append(data)
        except Exception as e:
            print(f"⚠️ Grafik ma'lumoti olinmadi: {e}")
            chart_dicts = []

    total_content = len(presentation_content)
    # Grafik slaydlarini teng taqsimlash uchun joylashtirish indekslari
    chart_positions = {}
    if chart_dicts and total_content > 0:
        step = max(1, total_content // (len(chart_dicts) + 1))
        for ci in range(len(chart_dicts)):
            pos = min(total_content - 1, step * (ci + 1))
            # bir indeksga ikki grafik tushmasligi uchun
            while pos in chart_positions and pos < total_content - 1:
                pos += 1
            chart_positions[pos] = ci

    total_slides = 1 + total_content + len(chart_dicts) + 1
    counter = 1  # titul

    used_charts = set()
    for i, item in enumerate(presentation_content):
        # Shu indeksdan keyin grafik slaydi kerakmi
        if i in chart_positions:
            ci = chart_positions[i]
            if ci not in used_charts:
                counter += 1
                _build_chart_slide(prs, theme, chart_dicts[ci], counter,
                                   total_slides, topic, chart_type=chart_type)
                used_charts.add(ci)

        counter += 1
        bullets = _clean_bullets(item.get("content", ""))
        _build_content_slide(
            prs, theme, item.get("title", f"Slayd {i+1}"), bullets,
            counter, total_slides, topic,
            image_path=item.get("image"), icons=use_icons,
        )

    # Qo'shilmay qolgan grafiklar (masalan kontent bo'sh) — oxiriga
    for ci in range(len(chart_dicts)):
        if ci not in used_charts:
            counter += 1
            _build_chart_slide(prs, theme, chart_dicts[ci], counter,
                               total_slides, topic, chart_type=chart_type)

    # Yakuniy slayd
    _build_closing_slide(prs, theme, doc_data)

    os.makedirs(temp_dir, exist_ok=True)
    unique_filename = f"PPTX_{uuid.uuid4().hex[:8]}.pptx"
    generated_file_path = os.path.join(temp_dir, unique_filename)
    prs.save(generated_file_path)
    print(f"✅ Prezentatsiya tayyor ({theme['name']}): {generated_file_path}")
    return generated_file_path
