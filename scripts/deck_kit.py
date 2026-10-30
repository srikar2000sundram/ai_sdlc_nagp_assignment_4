"""A small slide toolkit: describe a slide once, write it as a PowerPoint file and as a PDF.

A slide is a list of shapes (``Box``), text boxes (``Text``) and pictures (``Pic``) positioned in inches on a 13.333 x 7.5
inch page. Two writers draw the same description:

* ``write_pptx`` makes an editable .pptx with python-pptx (real text boxes, real pictures, speaker notes, slide titles).
* ``write_pdf`` makes the same slides as HTML and prints them with Chromium, so the PDF matches the deck.

Text is measured with the real Calibri / Cambria fonts (``lines_needed``) so layouts can size boxes before drawing, and
``write_pdf`` returns a warning for any text that does not fit its box after the PDF layout is made.
Needs: pip install python-pptx pillow playwright && playwright install chromium
"""

import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image, ImageFont

W, H = 13.333, 7.5

# Palette shared with the PDF guides and the diagrams.
NAVY, NAVY2, TEAL, TEAL_D, TEAL_SOFT = "0B1E3F", "13315F", "14B8A6", "0B7F7A", "E6F6F4"
INK, MUTED, LINE, PAPER, WHITE = "1B2638", "5D6B7C", "D9E1E9", "F4F7FB", "FFFFFF"
RED, RED_SOFT, AMBER, AMBER_SOFT = "B4452F", "FDEBE7", "9A6A00", "FFF4D6"
MINT = "4BE3D2"

HEAD, BODY, MONO = "Cambria", "Calibri", "Consolas"
FONT_FILES = {
    (BODY, False): "C:/Windows/Fonts/calibri.ttf", (BODY, True): "C:/Windows/Fonts/calibrib.ttf",
    (HEAD, False): "C:/Windows/Fonts/cambria.ttc", (HEAD, True): "C:/Windows/Fonts/cambriab.ttf",
}
LINE_HEIGHT = 1.2  # multiple of the font size used by both writers


@dataclass
class Run:
    """A piece of text with optional overrides of its paragraph's style."""

    text: str
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    color: Optional[str] = None
    font: Optional[str] = None


@dataclass
class Para:
    """One paragraph: runs plus its default style."""

    runs: list
    size: float = 14
    color: str = INK
    bold: bool = False
    italic: bool = False
    font: str = BODY
    align: str = "l"  # l, c, r
    after: float = 0  # points of space after
    bullet: bool = False


@dataclass
class Box:
    """A filled and/or outlined rectangle, rounded rectangle or oval."""

    x: float
    y: float
    w: float
    h: float
    fill: Optional[str] = None
    line: Optional[str] = None
    line_w: float = 1.0
    radius: float = 0.0
    alpha: float = 1.0
    line_alpha: float = 1.0
    shadow: bool = False
    oval: bool = False


@dataclass
class Text:
    """A text box. ``title`` marks the slide title (used for the outline in PowerPoint)."""

    x: float
    y: float
    w: float
    h: float
    paras: list
    anchor: str = "t"  # t, m, b
    pad: tuple = (0.0, 0.0, 0.0, 0.0)  # left, top, right, bottom in inches
    title: bool = False


@dataclass
class Pic:
    """A picture drawn exactly in its box (fit it first with ``fit``)."""

    x: float
    y: float
    w: float
    h: float
    path: str
    alt: str = ""


@dataclass
class Slide:
    """One slide: background colour, shapes in drawing order, speaker notes."""

    bg: str = WHITE
    items: list = field(default_factory=list)
    notes: str = ""

    def add(self, *items) -> None:
        """Append shapes in drawing order."""
        self.items.extend(items)


# ---------------------------------------------------------------- text helpers

def rich(text: str) -> list:
    """Turn ``**bold**`` and `code` markers into runs."""
    runs = []
    for part in re.split(r"(\*\*.+?\*\*|`.+?`)", text):
        if not part:
            continue
        if part.startswith("**"):
            runs.append(Run(part[2:-2], bold=True))
        elif part.startswith("`"):
            runs.append(Run(part[1:-1], font=MONO, color=TEAL_D))
        else:
            runs.append(Run(part))
    return runs


def plain(text: str) -> str:
    """The text without its markers."""
    return re.sub(r"\*\*(.+?)\*\*|`(.+?)`", lambda m: m.group(1) or m.group(2), text)


_fonts: dict = {}


def _font(name: str, bold: bool, size: float) -> ImageFont.FreeTypeFont:
    """A cached PIL font at ``size`` points scaled to 10 px per point."""
    key = (name, bold, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_FILES[(name, bold)], int(round(size * 10)))
    return _fonts[key]


def lines_needed(text: str, size: float, width: float, bold: bool = False, font: str = BODY) -> int:
    """How many lines ``text`` takes in a box ``width`` inches wide (greedy word wrap, real font metrics)."""
    face = _font(font, bold, size)
    limit = width * 72 * 10  # pixels at 10 px per point
    total = 0
    for paragraph in plain(text).split("\n"):
        words, current, count = paragraph.split(" "), "", 1
        for word in words:
            trial = word if not current else current + " " + word
            if face.getlength(trial) <= limit or not current:
                current = trial
            else:
                count += 1
                current = word
        total += count
    return total


def text_height(text: str, size: float, width: float, bold: bool = False, font: str = BODY, after: float = 0) -> float:
    """Inches of height the text needs (lines at 1.2 x size, plus paragraph spacing)."""
    paragraphs = text.split("\n")
    lines = lines_needed(text, size, width, bold, font)
    return lines * size * LINE_HEIGHT / 72 + max(len(paragraphs) - 1, 0) * after / 72


def para(text: str, size: float = 14, color: str = INK, bold: bool = False, font: str = BODY, align: str = "l",
         after: float = 0, bullet: bool = False, italic: bool = False) -> Para:
    """One paragraph from marked-up text."""
    return Para(rich(text), size=size, color=color, bold=bold, font=font, align=align, after=after, bullet=bullet, italic=italic)


def text(x, y, w, h, content, size: float = 14, color: str = INK, bold: bool = False, font: str = BODY, align: str = "l",
         anchor: str = "t", after: float = 0, bullets: bool = False, italic: bool = False, pad: tuple = (0, 0, 0, 0),
         title: bool = False) -> Text:
    """A text box from a string (one paragraph per line) or a list of strings."""
    items = content if isinstance(content, list) else content.split("\n")
    paras = [para(item, size, color, bold, font, align, after if index < len(items) - 1 else 0, bullets, italic) for index, item in enumerate(items)]
    return Text(x, y, w, h, paras, anchor=anchor, pad=pad, title=title)


def fit(path: str, x: float, y: float, w: float, h: float, alt: str = "", align: str = "c") -> Pic:
    """A picture scaled to fit inside the box, keeping its proportions, centred (or left-aligned with ``align='l'``)."""
    with Image.open(path) as image:
        width, height = image.size
    scale = min(w / width, h / height)
    pw, ph = width * scale, height * scale
    px = x + (w - pw) / 2 if align == "c" else x
    return Pic(px, y + (h - ph) / 2, pw, ph, str(path), alt)


# ---------------------------------------------------------------- PowerPoint

def write_pptx(slides: list, path: Path, title: str, subject: str) -> None:
    """Write the slides to an editable .pptx file."""
    from lxml import etree
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
    from pptx.oxml.ns import qn
    from pptx.util import Emu, Inches, Pt

    presentation = Presentation()
    presentation.slide_width, presentation.slide_height = Inches(W), Inches(H)
    presentation.core_properties.title = title
    presentation.core_properties.subject = subject
    presentation.core_properties.author = "Invoice Approval project"
    layout = presentation.slide_layouts[5]  # "Title Only"
    align_map = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}
    anchor_map = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}

    def alpha_on(color_element, alpha: float) -> None:
        """Make an <a:srgbClr> element translucent."""
        etree.SubElement(color_element, qn("a:alpha")).set("val", str(int(alpha * 100000)))

    def draw_box(slide, box: Box) -> None:
        """A rectangle, rounded rectangle or oval."""
        kind = MSO_SHAPE.OVAL if box.oval else (MSO_SHAPE.ROUNDED_RECTANGLE if box.radius > 0 else MSO_SHAPE.RECTANGLE)
        shape = slide.shapes.add_shape(kind, Inches(box.x), Inches(box.y), Inches(box.w), Inches(box.h))
        if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
            shape.adjustments[0] = min(0.5, box.radius / min(box.w, box.h))
        if box.fill:
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor.from_string(box.fill)
            if box.alpha < 1:
                alpha_on(shape._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr")), box.alpha)
        else:
            shape.fill.background()
        if box.line:
            shape.line.color.rgb = RGBColor.from_string(box.line)
            shape.line.width = Pt(box.line_w)
            if box.line_alpha < 1:
                alpha_on(shape._element.spPr.find(qn("a:ln")).find(qn("a:solidFill")).find(qn("a:srgbClr")), box.line_alpha)
        else:
            shape.line.fill.background()
        effects = etree.SubElement(shape._element.spPr, qn("a:effectLst"))
        if box.shadow:
            shadow = etree.SubElement(effects, qn("a:outerShdw"), blurRad="95250", dist="28575", dir="5400000", algn="t", rotWithShape="0")
            color = etree.SubElement(shadow, qn("a:srgbClr"), val=NAVY)
            alpha_on(color, 0.13)

    def fill_text(frame, item: Text) -> None:
        """Write the paragraphs of a text box into a text frame."""
        frame.word_wrap = True
        frame.auto_size = MSO_AUTO_SIZE.NONE
        frame.margin_left, frame.margin_top, frame.margin_right, frame.margin_bottom = (Inches(v) for v in item.pad)
        frame.vertical_anchor = anchor_map[item.anchor]
        for index, para_ in enumerate(item.paras):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.alignment = align_map[para_.align]
            paragraph.space_after = Pt(para_.after)
            paragraph.line_spacing = 1.0
            for run_ in para_.runs:
                run = paragraph.add_run()
                run.text = run_.text
                run.font.size = Pt(para_.size)
                run.font.name = run_.font or para_.font
                run.font.bold = para_.bold if run_.bold is None else run_.bold
                run.font.italic = para_.italic if run_.italic is None else run_.italic
                run.font.color.rgb = RGBColor.from_string(run_.color or para_.color)
            if para_.bullet:
                properties = paragraph._p.get_or_add_pPr()
                properties.set("marL", str(int(Emu(Inches(0.22)))))
                properties.set("indent", str(-int(Emu(Inches(0.22)))))
                etree.SubElement(etree.SubElement(properties, qn("a:buClr")), qn("a:srgbClr")).set("val", TEAL)
                etree.SubElement(properties, qn("a:buFont")).set("typeface", "Arial")
                etree.SubElement(properties, qn("a:buChar")).set("char", "\u2022")

    for spec in slides:
        slide = presentation.slides.add_slide(layout)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(spec.bg)
        title_shape = slide.shapes.title
        title_item = next((item for item in spec.items if isinstance(item, Text) and item.title), None)
        if title_item is None:
            title_shape._element.getparent().remove(title_shape._element)
        for item in spec.items:
            if isinstance(item, Box):
                draw_box(slide, item)
            elif isinstance(item, Pic):
                picture = slide.shapes.add_picture(item.path, Inches(item.x), Inches(item.y), Inches(item.w), Inches(item.h))
                picture._element.nvPicPr.cNvPr.set("descr", item.alt or Path(item.path).stem.replace("-", " "))
            elif isinstance(item, Text):
                if item.title:
                    shape = title_shape
                    shape.left, shape.top, shape.width, shape.height = Inches(item.x), Inches(item.y), Inches(item.w), Inches(item.h)
                else:
                    shape = slide.shapes.add_textbox(Inches(item.x), Inches(item.y), Inches(item.w), Inches(item.h))
                fill_text(shape.text_frame, item)
        if spec.notes:
            slide.notes_slide.notes_text_frame.text = spec.notes
    presentation.save(str(path))


# ---------------------------------------------------------------- PDF

def _rgba(color: str, alpha: float = 1.0) -> str:
    """CSS colour from hex and alpha."""
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _data_uri(path: str) -> str:
    """A picture as a data: URI, so the HTML renders from a blank page."""
    import base64
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def _html_for(slides: list) -> str:
    """All slides as one HTML document, one fixed-size page per slide."""
    pages = []
    for number, spec in enumerate(slides, 1):
        parts = []
        for item in spec.items:
            geometry = f"left:{item.x:.3f}in;top:{item.y:.3f}in;width:{item.w:.3f}in;height:{item.h:.3f}in;"
            if isinstance(item, Box):
                style = geometry
                if item.fill:
                    style += f"background:{_rgba(item.fill, item.alpha)};"
                if item.line:
                    style += f"border:{item.line_w}pt solid {_rgba(item.line, item.line_alpha)};"
                style += "border-radius:50%;" if item.oval else (f"border-radius:{item.radius}in;" if item.radius else "")
                if item.shadow:
                    style += "box-shadow:0 2px 7px rgba(11,30,63,.16);"
                parts.append(f'<div class="b" style="{style}"></div>')
            elif isinstance(item, Pic):
                parts.append(f'<img class="p" style="{geometry}" src="{_data_uri(item.path)}" alt="{html.escape(item.alt)}">')
            elif isinstance(item, Text):
                left, top, right, bottom = item.pad
                justify = {"t": "flex-start", "m": "center", "b": "flex-end"}[item.anchor]
                style = f"{geometry}padding:{top}in {right}in {bottom}in {left}in;justify-content:{justify};"
                body = []
                for para_ in item.paras:
                    spans = []
                    for run_ in para_.runs:
                        weight = para_.bold if run_.bold is None else run_.bold
                        italic = para_.italic if run_.italic is None else run_.italic
                        css = (f"font-family:{run_.font or para_.font};color:#{run_.color or para_.color};"
                               f"font-weight:{700 if weight else 400};font-style:{'italic' if italic else 'normal'};")
                        spans.append(f'<span style="{css}">{html.escape(run_.text)}</span>')
                    align = {"l": "left", "c": "center", "r": "right"}[para_.align]
                    bullet = '<span class="bu">\u2022</span>' if para_.bullet else ""
                    indent = "padding-left:.22in;" if para_.bullet else ""
                    body.append(f'<div class="pg" style="font-size:{para_.size}pt;text-align:{align};margin-bottom:{para_.after}pt;{indent}">{bullet}{"".join(spans) or "&nbsp;"}</div>')
                parts.append(f'<div class="t" data-slide="{number}" style="{style}">{"".join(body)}</div>')
        pages.append(f'<section class="s" style="background:#{spec.bg}">{"".join(parts)}</section>')
    css = (f"@page{{size:{W}in {H}in;margin:0}}*{{box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}}"
           "html,body{margin:0;padding:0}"
           f".s{{position:relative;width:{W}in;height:{H}in;overflow:hidden;page-break-after:always;break-after:page}}"
           ".b,.t,.p{position:absolute}.t{display:flex;flex-direction:column;overflow:hidden}"
           f".pg{{line-height:{LINE_HEIGHT};white-space:normal;overflow-wrap:break-word}}"
           ".pg span{white-space:pre-wrap}.bu{position:absolute;left:0;top:0;color:#" + TEAL + ";display:inline-block;width:.22in;text-indent:0;font-family:Arial}"
           ".pg{position:relative}.p{object-fit:contain}")
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(pages)}</body></html>"


def write_pdf(slides: list, path: Path, preview_dir: Optional[Path] = None) -> list:
    """Print the slides to a PDF and return a list of text-overflow warnings (empty when everything fits).

    With ``preview_dir`` every slide is also saved as a PNG there, to look at the layout.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(_html_for(slides), wait_until="load")
        page.wait_for_timeout(300)
        problems = page.evaluate(
            """() => [...document.querySelectorAll('.t')].filter(e => e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2)
                .map(e => 'slide ' + e.dataset.slide + ': ' + e.innerText.slice(0, 70).replace(/\\n/g, ' / '))"""
        )
        if preview_dir is not None:
            preview_dir.mkdir(parents=True, exist_ok=True)
            for index in range(len(slides)):
                page.locator("section.s").nth(index).screenshot(path=str(preview_dir / f"slide-{index + 1:02d}.png"))
        page.pdf(path=str(path), width=f"{W}in", height=f"{H}in", print_background=True, prefer_css_page_size=True)
        browser.close()
    return problems
