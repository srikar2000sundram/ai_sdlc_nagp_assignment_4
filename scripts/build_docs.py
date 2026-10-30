"""Build the project documentation as PDFs.

    python scripts/build_docs.py

Sources are Markdown files under docs/guides plus the spec, PR review, assignment and agent files already in the
repository. Output in docs/pdf/: one separate PDF per document (divider page + content).
Add --kit to build the three personal video-kit PDFs into For-Me-Video-Kit/ instead.
Add --combined to also build one merged Invoice-Approval-Complete-Documentation.pdf (cover, contents, every document).
Needs: pip install markdown pypdf playwright && playwright install chromium
"""

import base64
import html
import io
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent.parent
GUIDES = ROOT / "docs" / "guides"
SPECS = ROOT / "specs" / "001-invoice-approval-limits"
OUT = ROOT / "docs" / "pdf"
PROJECT = "Invoice Approval"
PROJECT_LONG = "Invoice Approval: Approval Limits by Role"
VERSION = "1.0"
TODAY = date.today().strftime("%d %B %Y").lstrip("0")
COMBINED_NAME = "Invoice-Approval-Complete-Documentation"
BUILD_COMBINED = "--combined" in sys.argv

# Palette: deep navy with a bright teal accent.
NAVY, NAVY_DEEP, TEAL, TEAL_DARK, TEAL_SOFT = "#0b1e3f", "#07142b", "#14b8a6", "#0b7f7a", "#e6f6f4"
INK, MUTED, RULE, ZEBRA = "#1b2638", "#5d6b7c", "#d9e1e9", "#f5f8fa"


@dataclass(frozen=True)
class Document:
    """One PDF to build: file name, title, subtitle and the Markdown files it is made from."""

    filename: str
    title: str
    subtitle: str
    sources: tuple[tuple[Path, str], ...]  # (file, section heading, or "" for a single-file document)


DOCUMENTS = [
    Document("01-Project-Overview", "Project Overview", "What was built, where it stands and where to read more",
             ((GUIDES / "01-project-overview.md", ""),)),
    Document("02-Requirements-Specification", "Requirements Specification", "Rules, decisions, boundaries and traceability",
             ((GUIDES / "02-requirements-specification.md", ""),)),
    Document("03-Architecture-and-Design", "Architecture and Design", "Layers, data model and design decisions",
             ((GUIDES / "03-architecture-and-design.md", ""),)),
    Document("04-API-Reference", "API Reference", "Endpoints, payloads, status codes and reason texts",
             ((GUIDES / "04-api-reference.md", ""),)),
    Document("05-User-Guide", "User Guide", "Using the web interface, step by step",
             ((GUIDES / "05-user-guide.md", ""),)),
    Document("06-Developer-Guide", "Developer Guide", "Setup, commands, conventions and troubleshooting",
             ((GUIDES / "06-developer-guide.md", ""),)),
    Document("07-Test-Plan-and-Report", "Test Plan and Report", "Strategy, coverage and why the tests can fail",
             ((GUIDES / "07-test-plan-and-report.md", ""),)),
    Document("08-Mutation-Testing-Report", "Mutation Testing Report", "Before and after scores, survivors and fixes",
             ((GUIDES / "08-mutation-testing-report.md", ""),)),
    Document("09-Code-Review-Report", "Code Review Report", "Every review finding and its verdict",
             ((ROOT / "docs" / "pr-review.md", ""),)),
    Document("10-AI-Workflow-Guide", "AI Workflow Guide", "Context file, skills, agents, hooks and the interaction log",
             ((GUIDES / "10-ai-workflow-guide.md", ""),)),
    Document("11-Operations-and-Security", "Operations and Security", "Controls, limits, follow-up work and release notes",
             ((GUIDES / "11-operations-and-security.md", ""),)),
    Document("12-Specification-Pack", "Specification Pack", "Constitution, specification, plan, contract and tasks",
             (
                 (ROOT / ".specify" / "memory" / "constitution.md", "Constitution"),
                 (SPECS / "spec.md", "Feature specification"),
                 (SPECS / "plan.md", "Implementation plan"),
                 (SPECS / "research.md", "Research and decisions"),
                 (SPECS / "data-model.md", "Data model"),
                 (SPECS / "contracts" / "approvals-api.md", "API contract"),
                 (SPECS / "quickstart.md", "Quickstart"),
                 (SPECS / "checklists" / "requirements.md", "Requirements checklist"),
                 (SPECS / "tasks.md", "Task list"),
             )),
    Document("13-Assignment-Report", "Assignment Report", "How each assignment item was met",
             ((ROOT / "ASSIGNMENT.md", ""),)),
    Document("14-Appendix-Conventions-and-Use-Cases", "Appendix", "Agent conventions and the feature briefs for future work",
             (
                 (ROOT / "AGENTS.md", "Agent conventions"),
                 (ROOT / "docs" / "use-cases" / "UC-1-bulk-approval.md", "Use case 1"),
                 (ROOT / "docs" / "use-cases" / "UC-2-partial-approval.md", "Use case 2"),
             )),
    Document("15-Demo-Video-Script", "Demo Video Script", "A timed, rehearsed script for the 8 to 10 minute recording",
             ((GUIDES / "15-demo-video-script.md", ""),)),
    Document("16-Submission-Checklist", "Submission Checklist", "What is done, what is open and what to watch for",
             ((GUIDES / "16-submission-checklist.md", ""),)),
    Document("17-Recording-Runbook", "Recording Runbook", "Step by step: from running the app to a finished video, with what to say",
             ((GUIDES / "17-recording-runbook.md", ""),)),
    Document("18-Run-and-Test-Guide", "Run and Test Guide", "How to run the project and check every case: one command, automated suites, or by hand",
             ((GUIDES / "18-run-and-test-guide.md", ""),)),
    Document("19-SOLID-Design", "SOLID Design", "How each principle is followed: the problem, the change and the proof",
             ((GUIDES / "19-solid-design.md", ""),)),
    Document("20-Code-Reference", "Code Reference", "Every module, class and function, generated from the docstrings",
             ((GUIDES / "20-code-reference.md", ""),)),
    Document("21-Architecture-Diagrams", "Architecture Diagrams", "The system, one request, the rules, the lifecycle, the AI workflow and the test layers, drawn from the code",
             ((GUIDES / "21-architecture-diagrams.md", ""),)),
    Document("22-Reviewer-Guide", "Reviewer Guide", "What to open, how to check every claim, what was decided and what is still open",
             ((GUIDES / "22-reviewer-guide.md", ""),)),
    Document("23-UI-Walkthrough", "UI Walkthrough", "The running application screen by screen, with real screenshots and the rule each one proves",
             ((GUIDES / "23-ui-walkthrough.md", ""),)),
]

BODY_CSS = f"""
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 10.3pt; line-height: 1.55; color: {INK}; margin: 0; }}
h1, h2, h3, h4 {{ color: {NAVY}; line-height: 1.25; font-weight: 600; }}
h1 {{ font-family: Georgia, "Times New Roman", serif; font-size: 24pt; font-weight: 400; margin: 0 0 8pt; }}
h2 {{ font-size: 15pt; margin: 22pt 0 8pt; padding-left: 10pt; border-left: 4px solid {TEAL}; break-after: avoid; }}
h3 {{ font-size: 12pt; color: {TEAL_DARK}; margin: 15pt 0 4pt; break-after: avoid; }}
h4 {{ font-size: 10.5pt; margin: 10pt 0 3pt; break-after: avoid; }}
p {{ margin: 5pt 0; }}
a {{ color: {TEAL_DARK}; text-decoration: none; }}
strong {{ color: {NAVY}; }}
code {{ font-family: Consolas, "Courier New", monospace; font-size: 8.8pt; color: #0a5e63; background: #eaf4f5; padding: 1px 4px; border-radius: 3px; }}
pre {{ background: #f4f7fa; border: 1px solid {RULE}; border-left: 3px solid {TEAL}; border-radius: 4px; padding: 9pt 11pt;
      white-space: pre-wrap; overflow-wrap: anywhere; break-inside: avoid; }}
pre code {{ background: none; color: {INK}; padding: 0; font-size: 8.6pt; }}
table {{ border-collapse: separate; border-spacing: 0; width: 100%; margin: 9pt 0; font-size: 9.2pt;
        border: 1px solid {RULE}; border-radius: 6px; overflow: hidden; }}
th {{ background: {NAVY}; color: #fff; text-align: left; font-weight: 600; padding: 6pt 8pt; letter-spacing: .02em; }}
td {{ padding: 5pt 8pt; vertical-align: top; overflow-wrap: anywhere; border-top: 1px solid #e7edf2; }}
tbody tr:nth-child(even) td {{ background: {ZEBRA}; }}
tr {{ break-inside: avoid; }}
table.step {{ break-inside: avoid; }}
table.step td.lab {{ width: 26%; white-space: nowrap; font-weight: 700; color: {NAVY}; }}
td.nw, td strong {{ white-space: nowrap; }}
img {{ max-width: 100%; max-height: 118mm; object-fit: contain; border: 1px solid {RULE}; border-radius: 6px;
      box-shadow: 0 2px 8px rgba(11,30,63,.12); margin: 8pt 0; break-inside: avoid; }}
blockquote {{ margin: 9pt 0; padding: 6pt 12pt; background: {TEAL_SOFT}; border-left: 3px solid {TEAL}; border-radius: 0 4px 4px 0; color: #28465a; }}
ul, ol {{ margin: 4pt 0; padding-left: 19pt; }}
li {{ margin: 2.5pt 0; }}
li::marker {{ color: {TEAL_DARK}; }}
hr {{ border: 0; border-top: 1px solid {RULE}; margin: 14pt 0; }}
.part {{ break-before: page; }}
.titleblock {{ margin: 0 0 14pt; padding-bottom: 12pt; border-bottom: 1px solid {RULE}; }}
.titleblock .kick {{ color: {TEAL_DARK}; letter-spacing: .28em; text-transform: uppercase; font-size: 8.5pt; font-weight: 600; }}
.titleblock h1 {{ font-size: 30pt; margin: 6pt 0 8pt; }}
.titleblock .bar {{ width: 70pt; height: 3px; background: {TEAL}; border-radius: 2px; }}
.titleblock p {{ color: {MUTED}; font-size: 11.5pt; margin: 9pt 0 0; }}
.toc h1 {{ margin-bottom: 4pt; }}
.toc .lead {{ color: {MUTED}; margin-bottom: 14pt; }}
.toc table {{ border: 0; border-radius: 0; overflow: visible; margin-top: 4pt; }}
.toc td {{ border: 0; border-bottom: 1px dotted #b5c2cf; padding: 4.4pt 2pt; background: none !important; vertical-align: middle; }}
.toc td.no {{ width: 34pt; color: {TEAL_DARK}; font-family: Georgia, serif; font-size: 13pt; }}
.toc td.pg {{ width: 36pt; text-align: right; color: {NAVY}; font-weight: 600; font-variant-numeric: tabular-nums; }}
.toc .t {{ color: {NAVY}; font-weight: 600; font-size: 10.6pt; }}
.toc .s {{ color: {MUTED}; font-size: 8.8pt; }}
"""

SHEET_CSS = f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html, body {{ margin: 0; padding: 0; }}
.sheet {{ position: relative; width: 210mm; height: 296.5mm; overflow: hidden; color: #fff;
         font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
         background: linear-gradient(158deg, {NAVY_DEEP} 0%, {NAVY} 52%, #0d3157 100%); }}
.orb {{ position: absolute; border-radius: 50%; }}
.o1 {{ width: 165mm; height: 165mm; right: -62mm; top: -58mm;
      background: radial-gradient(circle at 32% 32%, #2ed9c5 0%, {TEAL} 38%, #0c7c86 66%, rgba(12,124,134,0) 72%); opacity: .95; }}
.o2 {{ width: 118mm; height: 118mm; right: -30mm; top: -18mm; border: 1.2px solid rgba(255,255,255,.22); }}
.o3 {{ width: 80mm; height: 80mm; right: 6mm; top: 14mm; border: 1px solid rgba(255,255,255,.12); }}
.o4 {{ width: 70mm; height: 70mm; left: -34mm; bottom: -30mm; border: 1.2px solid rgba(20,184,166,.45); }}
.o5 {{ width: 110mm; height: 110mm; left: -52mm; bottom: -52mm; background: rgba(20,184,166,.12); }}
.body {{ position: absolute; left: 24mm; right: 24mm; top: 128mm; }}
.kicker {{ color: #4be3d2; font-size: 9pt; letter-spacing: .32em; text-transform: uppercase; font-weight: 600; }}
.num {{ font-family: Georgia, serif; font-size: 78pt; line-height: 1; color: rgba(75,227,210,.55); margin: 0 0 4mm -1mm; }}
.title {{ font-family: Georgia, "Times New Roman", serif; font-size: 36pt; line-height: 1.12; font-weight: 400; margin: 5mm 0 6mm; }}
.rule {{ width: 26mm; height: 3px; background: {TEAL}; border-radius: 2px; }}
.sub {{ font-size: 13pt; line-height: 1.5; color: #c6d6e8; margin-top: 7mm; max-width: 135mm; font-weight: 300; }}
.foot {{ position: absolute; left: 24mm; right: 24mm; bottom: 18mm; display: flex; justify-content: space-between;
        font-size: 8.8pt; letter-spacing: .06em; color: #94abc6; border-top: 1px solid rgba(255,255,255,.16); padding-top: 4mm; }}
.foot b {{ color: #e5eef8; font-weight: 600; }}
.cover .title {{ font-size: 40pt; white-space: nowrap; }}
.cover .body {{ top: 118mm; }}
.chips {{ margin-top: 12mm; display: flex; flex-wrap: wrap; gap: 6px; max-width: 150mm; }}
.chips span {{ font-size: 8.6pt; padding: 3px 10px; border: 1px solid rgba(75,227,210,.5); border-radius: 20px; color: #bff3ec; }}
"""

HEADER = (
    '<div style="width:100%;margin:0 20mm;padding-bottom:3px;border-bottom:1px solid #d9e1e9;display:flex;'
    "justify-content:space-between;font-family:'Segoe UI',Arial,sans-serif;font-size:7.5pt;letter-spacing:.14em;"
    'text-transform:uppercase;-webkit-print-color-adjust:exact;">'
    '<span style="color:#0b7f7a;font-weight:600;">{title}</span><span style="color:#8a97a6;">' + PROJECT + "</span></div>"
)
FOOTER = (
    '<div style="width:100%;margin:0 20mm;font-family:\'Segoe UI\',Arial,sans-serif;font-size:7.5pt;color:#8a97a6;'
    'display:flex;justify-content:space-between;letter-spacing:.04em;">'
    "<span>" + PROJECT_LONG + " &nbsp;·&nbsp; Version " + VERSION + "</span>"
    '<span style="color:#0b1e3f;font-weight:600;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>'
)


def strip_front_matter(text: str) -> str:
    """Remove a leading ``---`` YAML block (Spec Kit files have one)."""
    return re.sub(r"\A---\n.*?\n---\n", "", text.lstrip("﻿"), count=1, flags=re.S)


def shift_headings(text: str, levels: int) -> str:
    """Push every heading down by `levels`, ignoring lines inside code fences."""
    result, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"#{1,5} ", line):
            line = "#" * levels + line
        result.append(line)
    return "\n".join(result)


def drop_title(text: str) -> str:
    """Remove the first ``# Title`` line; the PDF shows its own title."""
    return re.sub(r"\A\s*# .+\n", "", text, count=1)


def inline_images(page_html: str, base_dir: Path) -> str:
    """Embed local images as data URIs so the HTML renders from anywhere."""

    def replace(match: re.Match) -> str:
        """Replace one image source with its data URI when the file exists."""
        source = match.group(1)
        image_path = (base_dir / source).resolve()
        if source.startswith(("http", "data:")) or not image_path.exists():
            return match.group(0)
        return f'src="data:image/png;base64,{base64.b64encode(image_path.read_bytes()).decode()}"'

    return re.sub(r'src="([^"]+)"', replace, page_html)


def drop_dead_links(page_html: str) -> str:
    """Relative links go nowhere inside a PDF: keep the text only."""
    return re.sub(r'<a href="(?!https?:|#|mailto:)[^"]*">(.*?)</a>', r"\1", page_html, flags=re.S)


def render_markdown(text: str) -> str:
    """Convert Markdown (tables, fenced code, lists) to HTML."""
    converted = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"]).convert(text)
    # Short cells (ids such as FR-001) must not wrap at the hyphen.
    return re.sub(r"<td>([^<\s][^<]{0,13})</td>", r'<td class="nw">\1</td>', converted)


def document_body(document: Document) -> str:
    """The HTML body of a document, joining several source files into sections when needed."""
    single = len(document.sources) == 1 and not document.sources[0][1]
    parts = []
    for path, section in document.sources:
        text = strip_front_matter(path.read_text(encoding="utf-8"))
        text = drop_title(text)
        if not single:
            text = f"## {section}\n\n" + shift_headings(text, 1)
        body = drop_dead_links(inline_images(render_markdown(text), path.parent))
        parts.append(body if single else f'<section class="part">{body}</section>')
    return "\n".join(parts)


def wrap(inner: str, css: str) -> str:
    """Wrap a body in a full HTML page with the given CSS."""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{inner}</body></html>"


def sheet(kind: str, title: str, subtitle: str, number: str = "", chips: tuple[str, ...] = ()) -> str:
    """HTML for a full-page cover or divider."""
    orbs = '<div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div><div class="orb o4"></div><div class="orb o5"></div>'
    chip_html = f'<div class="chips">{"".join(f"<span>{html.escape(c)}</span>" for c in chips)}</div>' if chips else ""
    number_html = f'<div class="num">{number}</div>' if number else ""
    label = "Invoice Approval  ·  Complete documentation" if kind == "cover" else "Document"
    return (
        f'<div class="sheet {kind}">{orbs}<div class="body"><div class="kicker">{label}</div>{number_html}'
        f'<div class="title">{html.escape(title)}</div><div class="rule"></div>'
        f'<div class="sub">{html.escape(subtitle)}</div>{chip_html}</div>'
        f'<div class="foot"><span><b>{html.escape(PROJECT)}</b> &nbsp;·&nbsp; Version {VERSION}</span><span>{TODAY}</span></div></div>'
    )


def pdf_bytes(browser, inner: str, css: str, *, full_bleed: bool, header_title: str = "") -> bytes:
    """Render HTML to PDF bytes with Chromium: full-bleed for sheets, with header and footer for content."""
    page = browser.new_page()
    page.set_content(wrap(inner, css), wait_until="load")
    if full_bleed:
        data = page.pdf(format="A4", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    else:
        options = dict(
            format="A4", print_background=True, display_header_footer=True,
            header_template=HEADER.format(title=html.escape(header_title)), footer_template=FOOTER,
            margin={"top": "24mm", "bottom": "20mm", "left": "20mm", "right": "20mm"},
        )
        data = page.pdf(**options)
    page.close()
    return data


def first_page_only(data: bytes) -> PdfReader:
    """A divider is one sheet; drop any spill-over page the renderer might add."""
    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(data)).pages[0])
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return PdfReader(buffer)


def toc_html(starts: list[int]) -> str:
    """HTML for the contents page of the combined PDF."""
    rows = "".join(
        f'<tr><td class="no">{index:02d}</td><td><div class="t">{html.escape(doc.title)}</div>'
        f'<div class="s">{html.escape(doc.subtitle)}</div></td><td class="pg">{start}</td></tr>'
        for index, (doc, start) in enumerate(zip(DOCUMENTS, starts), start=1)
    )
    return (
        f'<div class="toc"><h1>Contents</h1><div class="lead">Page numbers refer to the page of this PDF.</div>'
        f"<table><tbody>{rows}</tbody></table></div>"
    )


KIT = ROOT / "For-Me-Video-Kit"
KIT2 = ROOT / "For-Me-Submission-Kit"
KIT_DOCUMENTS = [
    Document("00-START-HERE-Complete-Guide-From-Zero", "Start Here: Complete Guide From Zero", "What was built, why, how to run it, what to show, what to say and how to say it",
             ((KIT / "src" / "00-start-here-complete-guide-from-zero.md", ""),)),
    Document("01-How-To-Run-The-App", "How to Run the App", "Start it, sign in, reset it, and be sure it works before you record",
             ((KIT / "src" / "01-how-to-run-the-app.md", ""),)),
    Document("02-What-To-Show", "What to Show", "The shot list: which window, what to point at, what the viewer should notice",
             ((KIT / "src" / "02-what-to-show.md", ""),)),
    Document("03-Video-Script-Step-By-Step", "Video Script, Step by Step", "Every action, every command and every word, in order",
             ((KIT / "src" / "03-video-script-step-by-step.md", ""),)),
    Document("04-Beginner-Demo-and-Hand-in-Guide", "Beginner's Guide: Demo and Hand-in", "What to do, where, and what to say, from the first command to the uploaded video",
             ((KIT / "src" / "04-beginner-demo-and-handin-guide.md", ""),)),
    Document("05-Minute-By-Minute-Demo-Script", "Minute-by-Minute Demo Script", "Ten minutes, to the second: what is on screen, what you do, what you say",
             ((KIT / "src" / "05-minute-by-minute-demo-script.md", ""),)),
    Document("06-Recording-Runbook", "Recording Runbook", "What to keep open, what to run first, then every step: show, do, say",
             ((KIT / "src" / "06-recording-runbook.md", ""),)),
    Document("01-Git-Commits-and-Pull-Request", "Git, Commits and Pull Request", "From an uncommitted folder to a pull request on your fork, step by step",
             ((KIT2 / "src" / "01-git-commits-and-pull-request.md", ""),)),
    Document("02-Questions-and-Answers-Prep", "Questions and Answers Prep", "Likely questions with short, honest answers",
             ((KIT2 / "src" / "02-questions-and-answers-prep.md", ""),)),
]


def build_kit() -> None:
    """Personal, printable guides: one PDF each, in For-Me-Video-Kit/ (git-ignored)."""
    for folder in (KIT, KIT2):
        folder.mkdir(exist_ok=True)
        for stale in folder.glob("*.pdf"):
            stale.unlink()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for document in KIT_DOCUMENTS:
            title_block = (f'<div class="titleblock"><div class="kick">{"Submission kit" if document.filename[:2] in ("01", "02") and "Git" in document.title or "Questions" in document.title else "Video kit"}</div><h1>{html.escape(document.title)}</h1>'
                           f'<div class="bar"></div><p>{html.escape(document.subtitle)}</p></div>')
            data = pdf_bytes(browser, title_block + document_body(document), BODY_CSS, full_bleed=False, header_title=document.title)
            reader = PdfReader(io.BytesIO(data))
            writer = PdfWriter()
            writer.append(reader)
            writer.add_metadata({"/Title": document.title, "/Subject": document.subtitle})
            target = document.sources[0][0].parent.parent / f"{document.filename}.pdf"
            with open(target, "wb") as handle:
                writer.write(handle)
            print(f"{target.name}: {len(reader.pages)} pages")
        browser.close()


def main() -> None:
    """Build every PDF (or, with ``--kit``, the personal kits; with ``--combined``, the merged file)."""
    if "--kit" in sys.argv:
        build_kit()
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.pdf"):
        stale.unlink()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        dividers, bodies = [], []
        for index, document in enumerate(DOCUMENTS, start=1):
            divider = sheet("divider", document.title, document.subtitle, number=f"{index:02d}")
            dividers.append(first_page_only(pdf_bytes(browser, divider, SHEET_CSS, full_bleed=True)))
            body = pdf_bytes(browser, document_body(document), BODY_CSS, full_bleed=False, header_title=document.title)
            bodies.append(PdfReader(io.BytesIO(body)))

            writer = PdfWriter()
            writer.append(dividers[-1])
            writer.append(bodies[-1])
            writer.add_outline_item(document.title, 0)
            writer.add_metadata({"/Title": f"{document.title} - {PROJECT_LONG}", "/Subject": document.subtitle})
            target = OUT / f"{document.filename}.pdf"
            with open(target, "wb") as handle:
                writer.write(handle)
            print(f"{target.name}: {1 + len(bodies[-1].pages)} pages")

        if BUILD_COMBINED:
            cover = first_page_only(pdf_bytes(
                browser,
                sheet("cover", "Approval Limits by Role", "Specification, design, verification and operations: the complete record of this delivery",
                      chips=("Python 3.13", "FastAPI", "pytest", "mutmut", "Playwright", "Spec Kit")),
                SHEET_CSS, full_bleed=True,
            ))

            # Contents: render once, check it fits on one page, then fix the page numbers (cover = 1, contents = 2).
            toc_pages = 1
            for _ in range(2):
                starts, next_page = [], 1 + toc_pages + 1
                for body in bodies:
                    starts.append(next_page)
                    next_page += 1 + len(body.pages)
                toc = PdfReader(io.BytesIO(pdf_bytes(browser, toc_html(starts), BODY_CSS, full_bleed=False, header_title="Contents")))
                if len(toc.pages) == toc_pages:
                    break
                toc_pages = len(toc.pages)
        browser.close()

    if BUILD_COMBINED:
        combined = PdfWriter()
        combined.append(cover)
        combined.add_outline_item("Cover", 0)
        combined.append(toc)
        combined.add_outline_item("Contents", 1)
        for document, divider, body in zip(DOCUMENTS, dividers, bodies):
            page_index = len(combined.pages)
            combined.append(divider)
            combined.append(body)
            combined.add_outline_item(document.title, page_index)
        combined.add_metadata({"/Title": f"Complete Documentation - {PROJECT_LONG}", "/Subject": "Invoice approval limits by role"})
        target = OUT / f"{COMBINED_NAME}.pdf"
        with open(target, "wb") as handle:
            combined.write(handle)
        print(f"{target.name}: {len(combined.pages)} pages (last contents entry points to page {starts[-1]})")


if __name__ == "__main__":
    main()
