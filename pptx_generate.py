"""
Zamonaviy PPTX generatori — SHABLON + RANG tizimi.

Ikki bosqichli tanlov:
  1) TEMPLATE (shablon uslubi) — 10 xil: butun prezentatsiyaning umumiy ko'rinishi
     (fon, shrift, layout oilasi, bullet uslubi, bezak).
  2) THEME (rang/dizayn) — 15 xil rang palitrasi.

Har bir slayd shu shablon uslubida IZCHIL chiziladi (tasodifiy emas).
Tashqi .pptx shablonga bog'liq emas — barchasi qo'lda chiziladi.
"""

import os
import uuid
import random

from pptx import Presentation
from pptx.util import Inches, Pt
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

WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CREAM = RGBColor(0xF6, 0xF1, 0xE7)
LIGHT_MUTED = RGBColor(0xAA, 0xB2, 0xC0)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


# ---------------------------------------------------------------------------
# 15 ta RANG palitrasi
# ---------------------------------------------------------------------------
def _C(r, g, b):
    return RGBColor(r, g, b)


def _mk(primary, accent, accent2, text, light, name):
    return {"name": name, "primary": _C(*primary), "accent": _C(*accent),
            "accent2": _C(*accent2), "text": _C(*text), "muted": _C(0x6B, 0x72, 0x80),
            "light": _C(*light), "on_dark": WHITE}


THEMES = {
    "ocean":    _mk((0x12, 0x2A, 0x4A), (0x3B, 0x82, 0xF6), (0x60, 0xA5, 0xFA), (0x1F, 0x2A, 0x37), (0xEF, 0xF4, 0xFB), "Okean"),
    "emerald":  _mk((0x0B, 0x3D, 0x2E), (0x10, 0xB9, 0x81), (0x34, 0xD3, 0x99), (0x18, 0x2A, 0x24), (0xEC, 0xFD, 0xF5), "Zumrad"),
    "sunset":   _mk((0x3B, 0x12, 0x3A), (0xF9, 0x73, 0x16), (0xFB, 0x92, 0x3C), (0x2A, 0x18, 0x29), (0xFD, 0xF2, 0xF8), "Shafaq"),
    "crimson":  _mk((0x4A, 0x0E, 0x12), (0xE1, 0x1D, 0x48), (0xFB, 0x71, 0x85), (0x2A, 0x14, 0x17), (0xFF, 0xF1, 0xF2), "Qirmizi"),
    "violet":   _mk((0x2E, 0x10, 0x65), (0x8B, 0x5C, 0xF6), (0xA7, 0x8B, 0xFA), (0x1E, 0x15, 0x35), (0xF5, 0xF3, 0xFF), "Binafsha"),
    "teal":     _mk((0x0A, 0x3A, 0x3A), (0x14, 0xB8, 0xA6), (0x2D, 0xD4, 0xBF), (0x14, 0x29, 0x2A), (0xF0, 0xFD, 0xFA), "Moviy-yashil"),
    "amber":    _mk((0x42, 0x20, 0x06), (0xF5, 0x9E, 0x0B), (0xFB, 0xBF, 0x24), (0x2A, 0x1C, 0x0A), (0xFF, 0xFB, 0xEB), "Kahrabo"),
    "indigo":   _mk((0x1E, 0x1B, 0x4B), (0x63, 0x66, 0xF1), (0x81, 0x8C, 0xF8), (0x1A, 0x1A, 0x2E), (0xEE, 0xF2, 0xFF), "Indigo"),
    "rose":     _mk((0x4C, 0x05, 0x19), (0xF4, 0x3F, 0x5E), (0xFB, 0x71, 0x85), (0x2A, 0x0E, 0x18), (0xFF, 0xF1, 0xF2), "Pushti"),
    "slate":    _mk((0x1E, 0x29, 0x3B), (0x38, 0xBD, 0xF8), (0x7D, 0xD3, 0xFC), (0x1E, 0x29, 0x3B), (0xF1, 0xF5, 0xF9), "Kulrang-ko'k"),
    "forest":   _mk((0x14, 0x36, 0x1F), (0x22, 0xC5, 0x5E), (0x4A, 0xDE, 0x80), (0x14, 0x27, 0x1A), (0xF0, 0xFD, 0xF4), "O'rmon"),
    "midnight": _mk((0x0B, 0x12, 0x20), (0x38, 0xBD, 0xF8), (0x81, 0x8C, 0xF8), (0x11, 0x18, 0x27), (0xEE, 0xF2, 0xFF), "Yarim tun"),
    "coral":    _mk((0x4A, 0x14, 0x10), (0xF9, 0x73, 0x62), (0xFC, 0xA5, 0xA5), (0x2A, 0x14, 0x10), (0xFF, 0xF1, 0xF0), "Marjon"),
    "cyan":     _mk((0x08, 0x33, 0x44), (0x06, 0xB6, 0xD4), (0x22, 0xD3, 0xEE), (0x0E, 0x2A, 0x33), (0xEC, 0xFE, 0xFF), "Siyohrang"),
    "plum":     _mk((0x3B, 0x07, 0x64), (0xC0, 0x26, 0xD3), (0xE8, 0x79, 0xF9), (0x2A, 0x10, 0x33), (0xFD, 0xF4, 0xFF), "Olxo'ri"),
}


# ---------------------------------------------------------------------------
# 10 ta SHABLON uslubi
#   bg:       light | dark | cream
#   title:    titul slayd varianti
#   content:  kontent layout oilasi
#   bullet:   arrow | dash | number | none
#   font:     shrift nomi
# ---------------------------------------------------------------------------
TEMPLATES = {
    "classic":     {"name": "Klassik",     "bg": "light", "title": "block",  "content": "standard", "bullet": "dash",   "font": "Georgia"},
    "minimalist":  {"name": "Minimalist",  "bg": "light", "title": "light",  "content": "minimal",  "bullet": "none",   "font": "Calibri"},
    "bold":        {"name": "Bold",        "bg": "light", "title": "split",   "content": "split",    "bullet": "arrow",  "font": "Arial"},
    "corporate":   {"name": "Korporativ",  "bg": "light", "title": "band",    "content": "band",     "bullet": "arrow",  "font": "Calibri"},
    "modern":      {"name": "Zamonaviy",   "bg": "light", "title": "block",   "content": "cards",    "bullet": "card",   "font": "Calibri"},
    "dark":        {"name": "Tungi",       "bg": "dark",  "title": "block",   "content": "standard", "bullet": "arrow",  "font": "Calibri"},
    "creative":    {"name": "Ijodiy",      "bg": "light", "title": "block",   "content": "creative", "bullet": "arrow",  "font": "Calibri"},
    "elegant":     {"name": "Nafis",       "bg": "cream", "title": "light",   "content": "minimal",  "bullet": "dash",   "font": "Georgia"},
    "infographic": {"name": "Infografik",  "bg": "light", "title": "band",    "content": "numbered", "bullet": "number", "font": "Calibri"},
    "photo":       {"name": "Rasm asosida","bg": "light", "title": "block",   "content": "photo",    "bullet": "arrow",  "font": "Calibri"},
}

ICON_MAP = [
    (("kirish", "introduction", "muqaddima"), "📖"),
    (("xulosa", "conclusion", "yakun"), "✅"),
    (("tarix", "history"), "🏛"),
    (("ta'rif", "tushuncha", "concept", "asosiy"), "💡"),
    (("texnologi", "technology", "tizim"), "⚙"),
    (("afzal", "advantage", "foyda"), "⭐"),
    (("muammo", "problem", "kamchilik"), "⚠"),
    (("statistik", "data", "ko'rsatkich", "ma'lumot"), "📊"),
    (("kelajak", "future", "istiqbol"), "🚀"),
    (("ta'lim", "education", "o'qit"), "🎓"),
]

CHART_TYPE_MAP = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar":    XL_CHART_TYPE.BAR_CLUSTERED,
    "pie":    XL_CHART_TYPE.PIE,
    "line":   XL_CHART_TYPE.LINE_MARKERS,
}


# ---------------------------------------------------------------------------
# Render konteksti (rang + shablon birgalikda)
# ---------------------------------------------------------------------------
def _ctx(theme, tpl):
    bgmode = tpl["bg"]
    if bgmode == "dark":
        bg, txt, titlec, footer, line = theme["primary"], theme["on_dark"], theme["on_dark"], LIGHT_MUTED, theme["accent2"]
    elif bgmode == "cream":
        bg, txt, titlec, footer, line = CREAM, theme["text"], theme["primary"], theme["muted"], theme["light"]
    else:
        bg, txt, titlec, footer, line = WHITE, theme["text"], theme["primary"], theme["muted"], theme["light"]
    return {
        "theme": theme, "font": tpl["font"], "bg": bg, "text": txt, "title": titlec,
        "accent": theme["accent"], "accent2": theme["accent2"], "primary": theme["primary"],
        "on_dark": theme["on_dark"], "footer": footer, "line": line,
        "bullet": tpl["bullet"], "family": tpl["content"], "title_kind": tpl["title"],
    }


# ---------------------------------------------------------------------------
# Past darajadagi yordamchilar
# ---------------------------------------------------------------------------
def _blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _fill_background(slide, color):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def _add_rect(slide, l, t, w, h, color, shape=MSO_SHAPE.RECTANGLE):
    sh = slide.shapes.add_shape(shape, l, t, w, h)
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def _add_text(slide, l, t, w, h, text, size, color, bold=False, align=PP_ALIGN.LEFT,
              anchor=MSO_ANCHOR.TOP, font="Calibri", italic=False, wrap=True):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    f = r.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.name = font
    f.color.rgb = color
    return box, tf


def _clean_bullets(raw):
    out = []
    for line in (raw or "").split("\n"):
        x = line.strip()
        if not x:
            continue
        x = x.lstrip("*-•▸●○◦·> ").strip().replace("**", "").strip()
        if x:
            out.append(x)
    return out


def _shorten(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def _pick_icon(title):
    t = (title or "").lower()
    for keys, emoji in ICON_MAP:
        if any(k in t for k in keys):
            return emoji
    return "📌"


def _marker(ctx, i):
    m = ctx["bullet"]
    if m == "number":
        return f"{i+1}.  "
    if m == "dash":
        return "—  "
    if m == "none":
        return ""
    return "▸  "


def _add_image_fit(slide, path, bl, bt, bw, bh):
    try:
        ratio = None
        if _HAS_PIL:
            with Image.open(path) as im:
                iw, ih = im.size
                if iw and ih:
                    ratio = iw / ih
        if ratio is None:
            ratio = bw / bh
        br = bw / bh
        if ratio > br:
            w = bw; h = int(bw / ratio)
        else:
            h = bh; w = int(bh * ratio)
        slide.shapes.add_picture(path, bl + (bw - w) // 2, bt + (bh - h) // 2, width=w, height=h)
        return True
    except Exception as e:
        print(f"⚠️ fit rasm xato: {e}")
        return False


def _add_image_cover(slide, path, l, t, w, h):
    try:
        if _HAS_PIL:
            with Image.open(path) as im:
                iw, ih = im.size
                target = w / h; src = iw / ih
                if src > target:
                    nw = int(ih * target); x0 = (iw - nw) // 2
                    im = im.crop((x0, 0, x0 + nw, ih))
                else:
                    nh = int(iw / target); y0 = (ih - nh) // 2
                    im = im.crop((0, y0, iw, y0 + nh))
                tmp = path + ".cover.jpg"
                im.convert("RGB").save(tmp)
                slide.shapes.add_picture(tmp, l, t, width=w, height=h)
                return True
        slide.shapes.add_picture(path, l, t, width=w, height=h)
        return True
    except Exception as e:
        print(f"⚠️ cover rasm xato: {e}")
        return _add_image_fit(slide, path, l, t, w, h)


def _img_frame(slide, ctx, path, l, t, w, h):
    _add_rect(slide, l - Inches(0.06), t - Inches(0.06), w + Inches(0.12), h + Inches(0.12), ctx["line"])
    _add_image_fit(slide, path, l, t, w, h)


def _bullets(slide, ctx, items, l, t, w, h, base, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    for i, line in enumerate(items):
        line = _shorten(line, 200)
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(9)
        p.line_spacing = 1.08
        mk = _marker(ctx, i)
        if mk:
            mr = p.add_run()
            mr.text = mk
            mr.font.size = Pt(base)
            mr.font.bold = True
            mr.font.name = ctx["font"]
            mr.font.color.rgb = ctx["accent"]
        r = p.add_run()
        r.text = line
        r.font.size = Pt(base)
        r.font.name = ctx["font"]
        r.font.color.rgb = ctx["text"]
    return box


def _cards(slide, ctx, items, l, t, w, total_h, base, numbered=False):
    n = max(1, len(items))
    gap = Inches(0.14)
    ch = int((total_h - gap * (n - 1)) / n)
    for i, line in enumerate(items):
        y = t + i * (ch + gap)
        _add_rect(slide, l, y, w, ch, ctx["theme"]["light"], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        _add_rect(slide, l, y, Inches(0.16), ch, ctx["accent"])
        tx = l + Inches(0.4)
        if numbered:
            _add_text(slide, l + Inches(0.3), y, Inches(0.7), ch, str(i + 1),
                      base + 4, ctx["accent"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
            tx = l + Inches(1.0)
        tb = slide.shapes.add_textbox(tx, y, l + w - tx - Inches(0.2), ch)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = _shorten(line, 130)
        r.font.size = Pt(base)
        r.font.name = ctx["font"]
        r.font.color.rgb = ctx["theme"]["text"]


def _add_footer(slide, ctx, index, total, topic, show_topic=True):
    _add_rect(slide, Inches(0.9), Inches(6.95), Inches(11.53), Inches(0.02), ctx["line"])
    if show_topic:
        _add_text(slide, Inches(0.9), Inches(7.0), Inches(9.0), Inches(0.4),
                  (topic or "")[:60], 10, ctx["footer"], font=ctx["font"])
    _add_text(slide, Inches(11.0), Inches(7.0), Inches(1.43), Inches(0.4),
              f"{index} / {total}", 10, ctx["footer"], align=PP_ALIGN.RIGHT, font=ctx["font"])


def _header(slide, ctx, title, icons=False):
    """Standart yuqori sarlavha (aksent kvadrat + sarlavha + nozik chiziq)."""
    _add_rect(slide, Inches(0.9), Inches(0.62), Inches(0.18), Inches(0.7), ctx["accent"])
    tl = Inches(1.25)
    if icons:
        _add_text(slide, Inches(1.25), Inches(0.45), Inches(0.9), Inches(1.0),
                  _pick_icon(title), 26, ctx["title"], anchor=MSO_ANCHOR.MIDDLE, font="Segoe UI Emoji")
        tl = Inches(2.1)
    _add_text(slide, tl, Inches(0.5), Inches(10.5), Inches(1.0),
              title, 27, ctx["title"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    _add_rect(slide, Inches(0.9), Inches(1.55), Inches(11.53), Inches(0.03), ctx["line"])


# ---------------------------------------------------------------------------
# Kontent layout OILALARI  (s, ctx, title, bullets, hi, ip, icons, parity)
# ---------------------------------------------------------------------------
def _fam_standard(s, ctx, title, b, hi, ip, icons, parity):
    _header(s, ctx, title, icons=icons)
    if hi and parity % 2 == 0:
        _bullets(s, ctx, b[:4], Inches(1.0), Inches(1.95), Inches(6.4), Inches(4.8), 16)
        _img_frame(s, ctx, ip, Inches(7.75), Inches(1.95), Inches(4.6), Inches(4.5))
    elif hi:
        _img_frame(s, ctx, ip, Inches(0.95), Inches(1.95), Inches(4.6), Inches(4.5))
        _bullets(s, ctx, b[:4], Inches(5.95), Inches(1.95), Inches(6.4), Inches(4.8), 16)
    else:
        _bullets(s, ctx, b[:6], Inches(1.0), Inches(1.95), Inches(11.3), Inches(4.8), 17)


def _fam_band(s, ctx, title, b, hi, ip, icons, parity):
    _add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(1.5), ctx["primary"])
    _add_rect(s, Inches(0), Inches(1.5), SLIDE_W, Inches(0.08), ctx["accent"])
    tl = Inches(0.9)
    if icons:
        _add_text(s, Inches(0.9), Inches(0.25), Inches(0.9), Inches(1.0), _pick_icon(title),
                  26, ctx["on_dark"], anchor=MSO_ANCHOR.MIDDLE, font="Segoe UI Emoji")
        tl = Inches(1.7)
    _add_text(s, tl, Inches(0.3), Inches(11.0), Inches(0.95), title, 26, ctx["on_dark"],
              bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    if hi:
        _bullets(s, ctx, b[:4], Inches(1.0), Inches(1.95), Inches(6.4), Inches(4.7), 16)
        _img_frame(s, ctx, ip, Inches(7.75), Inches(1.95), Inches(4.6), Inches(4.4))
    else:
        _bullets(s, ctx, b[:6], Inches(1.0), Inches(1.95), Inches(11.3), Inches(4.7), 17)


def _fam_sidepanel(s, ctx, title, b, hi, ip, icons, parity):
    _add_rect(s, Inches(0), Inches(0), Inches(4.3), SLIDE_H, ctx["primary"])
    _add_rect(s, Inches(4.3), Inches(0), Inches(0.08), SLIDE_H, ctx["accent"])
    if icons:
        _add_text(s, Inches(0.6), Inches(0.7), Inches(1.0), Inches(1.0), _pick_icon(title),
                  30, ctx["on_dark"], anchor=MSO_ANCHOR.MIDDLE, font="Segoe UI Emoji")
    _add_text(s, Inches(0.6), Inches(1.9), Inches(3.3), Inches(3.0), title, 26, ctx["on_dark"], bold=True, font=ctx["font"])
    _add_rect(s, Inches(0.62), Inches(5.0), Inches(1.6), Inches(0.08), ctx["accent2"])
    if hi:
        _add_image_cover(s, ip, Inches(0.6), Inches(5.3), Inches(3.1), Inches(1.6))
    _bullets(s, ctx, b[:6], Inches(4.8), Inches(1.6), Inches(7.7), Inches(4.9), 17)


def _fam_split(s, ctx, title, b, hi, ip, icons, parity):
    _add_rect(s, Inches(0), Inches(0), Inches(5.4), SLIDE_H, ctx["primary"])
    _add_text(s, Inches(0.7), Inches(1.4), Inches(4.2), Inches(2.8), title, 32, ctx["on_dark"], bold=True, font=ctx["font"])
    _add_rect(s, Inches(0.72), Inches(4.4), Inches(1.8), Inches(0.1), ctx["accent"])
    if hi:
        _add_image_cover(s, ip, Inches(0.7), Inches(4.8), Inches(4.0), Inches(2.0))
    _bullets(s, ctx, b[:5], Inches(5.9), Inches(1.6), Inches(6.6), Inches(4.9), 17)


def _fam_cards(s, ctx, title, b, hi, ip, icons, parity):
    _header(s, ctx, title, icons=icons)
    numbered = ctx["bullet"] == "number"
    if hi:
        _cards(s, ctx, b[:4], Inches(1.0), Inches(1.95), Inches(6.4), Inches(4.6), 15, numbered)
        _img_frame(s, ctx, ip, Inches(7.75), Inches(1.95), Inches(4.6), Inches(4.5))
    else:
        _cards(s, ctx, b[:5], Inches(1.0), Inches(1.95), Inches(11.3), Inches(4.7), 16, numbered)


def _fam_numbered(s, ctx, title, b, hi, ip, icons, parity):
    _fam_cards(s, ctx, title, b, hi, ip, icons, parity)


def _fam_minimal(s, ctx, title, b, hi, ip, icons, parity):
    _add_rect(s, Inches(1.0), Inches(0.9), Inches(0.5), Inches(0.07), ctx["accent"])
    _add_text(s, Inches(1.0), Inches(1.1), Inches(11.0), Inches(1.0), title, 30, ctx["title"], bold=True, font=ctx["font"])
    if hi and parity % 2 == 0:
        _bullets(s, ctx, b[:4], Inches(1.0), Inches(2.6), Inches(6.6), Inches(4.0), 17)
        _add_image_cover(s, ip, Inches(8.0), Inches(2.6), Inches(4.3), Inches(3.8))
    else:
        _bullets(s, ctx, b[:5], Inches(1.0), Inches(2.6), Inches(11.0), Inches(4.0), 18)


def _fam_creative(s, ctx, title, b, hi, ip, icons, parity):
    _add_rect(s, Inches(0), Inches(0), Inches(1.4), Inches(1.4), ctx["accent"], shape=MSO_SHAPE.RIGHT_TRIANGLE)
    tri = _add_rect(s, Inches(12.0), Inches(6.1), Inches(1.33), Inches(1.4), ctx["accent2"], shape=MSO_SHAPE.RIGHT_TRIANGLE)
    tri.rotation = 180
    _add_text(s, Inches(1.0), Inches(0.7), Inches(11.0), Inches(1.0), title, 28, ctx["title"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    _add_rect(s, Inches(1.0), Inches(1.7), Inches(2.2), Inches(0.08), ctx["accent"])
    if hi:
        _bullets(s, ctx, b[:4], Inches(1.0), Inches(2.1), Inches(6.4), Inches(4.5), 16)
        _img_frame(s, ctx, ip, Inches(7.75), Inches(2.0), Inches(4.5), Inches(4.4))
    else:
        _bullets(s, ctx, b[:6], Inches(1.0), Inches(2.1), Inches(11.3), Inches(4.5), 17)


def _fam_photo(s, ctx, title, b, hi, ip, icons, parity):
    if hi and parity % 2 == 0:
        _add_image_cover(s, ip, Inches(0), Inches(0), Inches(5.2), SLIDE_H)
        _add_text(s, Inches(5.7), Inches(0.7), Inches(7.0), Inches(1.0), title, 27, ctx["title"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
        _add_rect(s, Inches(5.7), Inches(1.7), Inches(2.0), Inches(0.08), ctx["accent"])
        _bullets(s, ctx, b[:5], Inches(5.7), Inches(2.0), Inches(7.0), Inches(4.6), 16)
    elif hi:
        _add_image_cover(s, ip, Inches(8.13), Inches(0), Inches(5.2), SLIDE_H)
        _add_text(s, Inches(0.9), Inches(0.7), Inches(6.8), Inches(1.0), title, 27, ctx["title"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
        _add_rect(s, Inches(0.9), Inches(1.7), Inches(2.0), Inches(0.08), ctx["accent"])
        _bullets(s, ctx, b[:5], Inches(0.9), Inches(2.0), Inches(6.8), Inches(4.6), 16)
    else:
        _fam_band(s, ctx, title, b, hi, ip, icons, parity)


_FAMILIES = {
    "standard": _fam_standard, "band": _fam_band, "sidepanel": _fam_sidepanel,
    "split": _fam_split, "cards": _fam_cards, "numbered": _fam_numbered,
    "minimal": _fam_minimal, "creative": _fam_creative, "photo": _fam_photo,
}
# Quyuq chap panelli oilalar — footer mavzu matni o'chiriladi
_PANEL_FAMILIES = {"sidepanel", "split"}


# ---------------------------------------------------------------------------
# TITUL slayd variantlari
# ---------------------------------------------------------------------------
def _title_info(slide, ctx, d, color):
    info = [f"Bajardi:  {d.get('student_fio', '')}",
            f"Guruh:  {d.get('student_group', '')}",
            f"Yil:  {d.get('year', '')}"]
    box = slide.shapes.add_textbox(Inches(0.9), Inches(5.6), Inches(7.0), Inches(1.5))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(info):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = line
        r.font.size = Pt(15)
        r.font.name = ctx["font"]
        r.font.color.rgb = color
        p.space_after = Pt(2)


def _title_block(prs, ctx, d):
    s = _blank_slide(prs)
    _fill_background(s, ctx["primary"])
    _add_rect(s, Inches(0), Inches(0), Inches(0.28), SLIDE_H, ctx["accent"])
    _add_rect(s, Inches(11.2), Inches(0), Inches(2.13), Inches(2.2), ctx["accent"])
    _add_rect(s, Inches(10.4), Inches(0), Inches(0.7), Inches(1.3), ctx["accent2"])
    uni = d.get("university_name") or d.get("uni_kafedra", "")
    kaf = d.get("uni_kafedra", "")
    _add_text(s, Inches(0.9), Inches(0.9), Inches(9.5), Inches(0.9), str(uni).upper(), 16, ctx["on_dark"], bold=True, font=ctx["font"])
    if kaf and kaf != uni:
        _add_text(s, Inches(0.9), Inches(1.55), Inches(9.5), Inches(0.6), str(kaf), 13, ctx["accent2"], font=ctx["font"])
    _add_text(s, Inches(0.9), Inches(2.7), Inches(11.0), Inches(2.2), d.get("topic", "Mavzu"), 40, ctx["on_dark"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    _add_rect(s, Inches(0.95), Inches(4.95), Inches(2.6), Inches(0.08), ctx["accent"])
    _title_info(s, ctx, d, ctx["on_dark"])
    return s


def _title_split(prs, ctx, d):
    s = _blank_slide(prs)
    _fill_background(s, WHITE)
    _add_rect(s, Inches(0), Inches(0), Inches(6.0), SLIDE_H, ctx["primary"])
    _add_rect(s, Inches(6.0), Inches(0), Inches(0.12), SLIDE_H, ctx["accent"])
    uni = d.get("university_name") or d.get("uni_kafedra", "")
    _add_text(s, Inches(0.7), Inches(0.8), Inches(4.8), Inches(0.9), str(uni).upper(), 14, ctx["on_dark"], bold=True, font=ctx["font"])
    _add_text(s, Inches(0.7), Inches(2.5), Inches(4.8), Inches(2.6), d.get("topic", "Mavzu"), 34, ctx["on_dark"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    _add_rect(s, Inches(0.72), Inches(5.2), Inches(1.8), Inches(0.1), ctx["accent"])
    info = [f"Bajardi:  {d.get('student_fio', '')}", f"Guruh:  {d.get('student_group', '')}", f"Yil:  {d.get('year', '')}"]
    tb = s.shapes.add_textbox(Inches(6.6), Inches(2.8), Inches(6.0), Inches(2.0))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(info):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = line
        r.font.size = Pt(16)
        r.font.name = ctx["font"]
        r.font.color.rgb = ctx["text"]
        p.space_after = Pt(4)
    return s


def _title_band(prs, ctx, d):
    s = _blank_slide(prs)
    _fill_background(s, WHITE)
    _add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(2.0), ctx["primary"])
    _add_rect(s, Inches(0), Inches(2.0), SLIDE_W, Inches(0.1), ctx["accent"])
    uni = d.get("university_name") or d.get("uni_kafedra", "")
    _add_text(s, Inches(0.9), Inches(0.6), Inches(11.0), Inches(0.9), str(uni).upper(), 16, ctx["on_dark"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    _add_text(s, Inches(0.9), Inches(2.9), Inches(11.5), Inches(2.0), d.get("topic", "Mavzu"), 38, ctx["primary"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    _add_rect(s, Inches(0.95), Inches(5.0), Inches(2.6), Inches(0.08), ctx["accent"])
    _title_info(s, ctx, d, ctx["text"])
    return s


def _title_light(prs, ctx, d):
    s = _blank_slide(prs)
    _fill_background(s, ctx["bg"] if ctx["bg"] != ctx["primary"] else WHITE)
    _add_rect(s, Inches(0), Inches(0), Inches(0.28), SLIDE_H, ctx["accent"])
    uni = d.get("university_name") or d.get("uni_kafedra", "")
    _add_text(s, Inches(1.0), Inches(0.9), Inches(10.0), Inches(0.9), str(uni).upper(), 15, ctx["primary"], bold=True, font=ctx["font"])
    _add_text(s, Inches(1.0), Inches(2.7), Inches(11.0), Inches(2.0), d.get("topic", "Mavzu"), 38, ctx["primary"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    _add_rect(s, Inches(1.05), Inches(4.8), Inches(2.4), Inches(0.07), ctx["accent"])
    _title_info(s, ctx, d, ctx["text"])
    return s


_TITLES = {"block": _title_block, "split": _title_split, "band": _title_band, "light": _title_light}


# ---------------------------------------------------------------------------
# Kontent / grafik / yakun slaydlari
# ---------------------------------------------------------------------------
def _build_content_slide(prs, ctx, title, bullets, index, total, topic, image_path, icons, parity):
    s = _blank_slide(prs)
    _fill_background(s, ctx["bg"])
    if not bullets:
        bullets = ["Ma'lumot generatsiya qilinmadi."]
    hi = bool(image_path) and os.path.exists(image_path or "")
    fam = ctx["family"]
    try:
        _FAMILIES[fam](s, ctx, title, bullets, hi, image_path, icons, parity)
    except Exception as e:
        print(f"⚠️ '{fam}' oila xato, standartga qaytildi: {e}")
        _fam_standard(s, ctx, title, bullets, hi, image_path, icons, parity)
    _add_footer(s, ctx, index, total, topic, show_topic=(fam not in _PANEL_FAMILIES))
    return s


def _build_chart_slide(prs, ctx, cd, index, total, topic, chart_type="column"):
    s = _blank_slide(prs)
    _fill_background(s, ctx["bg"])
    theme = ctx["theme"]
    _header(s, ctx, cd.get("title") or "Statistik ko'rsatkichlar")
    xl = CHART_TYPE_MAP.get(chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)
    chd = CategoryChartData()
    chd.categories = cd["categories"]
    if xl == XL_CHART_TYPE.PIE:
        f = cd["series"][0]
        chd.add_series(f["name"], f["values"])
    else:
        for ser in cd["series"]:
            chd.add_series(ser["name"], ser["values"])
    gf = s.shapes.add_chart(xl, Inches(1.2), Inches(1.95), Inches(10.9), Inches(4.8), chd)
    ch = gf.chart
    ch.has_title = False
    if xl == XL_CHART_TYPE.PIE:
        ch.has_legend = True
        ch.legend.position = XL_LEGEND_POSITION.RIGHT
        ch.legend.include_in_layout = False
        try:
            pts = ch.plots[0].series[0].points
            pal = [theme["accent"], theme["accent2"], theme["primary"], theme["muted"], _C(0x93, 0xC5, 0xFD)]
            for i, pt in enumerate(pts):
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = pal[i % len(pal)]
        except Exception:
            pass
    else:
        ch.has_legend = len(cd["series"]) > 1
        if ch.has_legend:
            ch.legend.position = XL_LEGEND_POSITION.BOTTOM
            ch.legend.include_in_layout = False
        try:
            pal = [theme["accent"], theme["accent2"], theme["primary"]]
            for si, ps in enumerate(ch.series):
                ps.format.fill.solid()
                ps.format.fill.fore_color.rgb = pal[si % len(pal)]
        except Exception:
            pass
    _add_footer(s, ctx, index, total, topic)
    return s


def _build_closing_slide(prs, ctx, d):
    s = _blank_slide(prs)
    _fill_background(s, ctx["primary"])
    _add_rect(s, Inches(0), Inches(0), Inches(0.28), SLIDE_H, ctx["accent"])
    _add_text(s, Inches(0.9), Inches(2.7), Inches(11.5), Inches(1.6), "E'tiboringiz uchun rahmat!", 44, ctx["on_dark"], bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, font=ctx["font"])
    _add_rect(s, Inches(5.86), Inches(4.4), Inches(1.6), Inches(0.08), ctx["accent"])
    _add_text(s, Inches(0.9), Inches(4.7), Inches(11.5), Inches(0.8), str(d.get("student_fio", "")), 18, ctx["accent2"], align=PP_ALIGN.CENTER, font=ctx["font"])
    return s


# ---------------------------------------------------------------------------
# Asosiy funksiya
# ---------------------------------------------------------------------------
async def generate_pptx_file(doc_data, presentation_content, temp_dir,
                             theme_name=None, template_name=None, options=None, theme_path=None):
    """
    doc_data: {topic, student_fio, student_group, uni_kafedra, university_name, year}
    presentation_content: [{"title", "content", "image"}]
    theme_name: 15 rangdan biri (None -> tasodifiy)
    template_name: 10 shablondan biri (None -> 'classic')
    options: {"images","icons","chart_type","chart_count"}
    """
    options = options or {}
    use_icons = bool(options.get("icons"))
    chart_type = options.get("chart_type")
    chart_count = int(options.get("chart_count") or 0)
    if not chart_type:
        chart_count = 0

    if theme_name not in THEMES:
        theme_name = random.choice(list(THEMES.keys()))
    if template_name not in TEMPLATES:
        template_name = "classic"
    theme = THEMES[theme_name]
    tpl = TEMPLATES[template_name]
    ctx = _ctx(theme, tpl)

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    topic = doc_data.get("topic", "Mavzu")

    # Titul slayd (shablonga mos variant)
    _TITLES.get(ctx["title_kind"], _title_block)(prs, ctx, doc_data)

    # Grafik ma'lumotlari
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

    tc = len(presentation_content)
    chart_positions = {}
    if chart_dicts and tc > 0:
        step = max(1, tc // (len(chart_dicts) + 1))
        for ci in range(len(chart_dicts)):
            pos = min(tc - 1, step * (ci + 1))
            while pos in chart_positions and pos < tc - 1:
                pos += 1
            chart_positions[pos] = ci

    total_slides = 1 + tc + len(chart_dicts) + 1
    counter = 1
    used = set()
    for i, item in enumerate(presentation_content):
        if i in chart_positions:
            ci = chart_positions[i]
            if ci not in used:
                counter += 1
                _build_chart_slide(prs, ctx, chart_dicts[ci], counter, total_slides, topic, chart_type=chart_type)
                used.add(ci)
        counter += 1
        bullets = _clean_bullets(item.get("content", ""))
        _build_content_slide(prs, ctx, item.get("title", f"Slayd {i+1}"), bullets,
                             counter, total_slides, topic, item.get("image"), use_icons, parity=i)

    for ci in range(len(chart_dicts)):
        if ci not in used:
            counter += 1
            _build_chart_slide(prs, ctx, chart_dicts[ci], counter, total_slides, topic, chart_type=chart_type)

    _build_closing_slide(prs, ctx, doc_data)

    os.makedirs(temp_dir, exist_ok=True)
    fp = os.path.join(temp_dir, f"PPTX_{uuid.uuid4().hex[:8]}.pptx")
    prs.save(fp)
    print(f"✅ Tayyor — shablon: {tpl['name']}, rang: {theme['name']} -> {fp}")
    return fp
