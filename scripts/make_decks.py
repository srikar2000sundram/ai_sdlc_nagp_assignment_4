"""Build the two slide decks (PowerPoint + PDF each) into docs/presentations/.

    python scripts/make_decks.py

* Invoice-Approval-Reviewer-Walkthrough: the whole project for a reviewer, from the rules to the evidence.
* Invoice-Approval-UI-Walkthrough: the running application, screen by screen, using the cropped screenshots.

Run these first if the pictures changed:  python scripts/ui_screens.py  and  python scripts/make_diagrams.py
Layout lives here; drawing lives in scripts/deck_kit.py.
"""

import os
import sys
from datetime import date
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deck_kit import (AMBER, HEAD, INK, LINE, MINT, MONO, MUTED, NAVY, PAPER, TEAL, TEAL_D, TEAL_SOFT, WHITE,  # noqa: E402
                      Box, Slide, fit, text, text_height, write_pdf, write_pptx)

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "guides" / "img"
UI, DIAGRAMS = IMAGES / "ui", IMAGES / "diagrams"
OUT = ROOT / "docs" / "presentations"
TODAY = date.today().strftime("%d %B %Y").lstrip("0")
FOOTER = "Invoice Approval  ·  Approval limits by role"
LIGHT_ON_NAVY = "C6D6E8"
CONTENT_BOTTOM = 6.85  # nothing may be drawn below this line (the footer lives under it)


class Deck:
    """The slides of one deck, with page numbers added at the end."""

    def __init__(self, title: str, subject: str) -> None:
        """Start an empty deck."""
        self.title, self.subject, self.slides, self.numbered = title, subject, [], set()

    def add(self, slide: Slide, numbered: bool = True) -> Slide:
        """Append a slide; ``numbered`` slides get the footer and page number."""
        self.slides.append(slide)
        if numbered:
            self.numbered.add(len(self.slides) - 1)
        return slide

    def build(self, name: str) -> None:
        """Write name.pptx and name.pdf and report any text that overflows."""
        for index in self.numbered:
            self.slides[index].add(text(0.6, 7.04, 8, 0.28, FOOTER, size=10, color=MUTED),
                                   text(11.5, 7.04, 1.23, 0.28, str(index + 1), size=10, color=MUTED, align="r"))
        OUT.mkdir(parents=True, exist_ok=True)
        write_pptx(self.slides, OUT / f"{name}.pptx", self.title, self.subject)
        preview = os.environ.get("DECK_PREVIEW")
        problems = write_pdf(self.slides, OUT / f"{name}.pdf", Path(preview) / name if preview else None)
        print(f"{name}: {len(self.slides)} slides" + (f", {len(problems)} text overflow(s):" if problems else ", every text fits"))
        for problem in problems:
            print("   ", problem)


# ------------------------------------------------------------------ slide frames

def dark_background(slide: Slide) -> None:
    """The navy page with the circles used on title, section and closing slides."""
    slide.bg = NAVY
    slide.add(Box(8.9, -2.7, 7.8, 7.8, fill=TEAL, alpha=0.88, oval=True),
              Box(7.7, -3.4, 8.6, 8.6, line=WHITE, line_alpha=0.2, line_w=1.2, oval=True),
              Box(9.6, -1.4, 5.6, 5.6, line=WHITE, line_alpha=0.12, line_w=1, oval=True),
              Box(-1.4, 5.1, 3.4, 3.4, line=TEAL, line_alpha=0.5, line_w=1.2, oval=True),
              Box(-2.3, 5.4, 4.6, 4.6, fill=TEAL, alpha=0.12, oval=True))


def title_slide(deck: Deck, kicker: str, title: str, subtitle: str, chips: list, notes: str = "", edition: str = "Reviewer edition") -> None:
    """The opening slide."""
    slide = Slide(notes=notes)
    dark_background(slide)
    slide.add(text(0.9, 1.9, 8, 0.3, kicker.upper(), size=13, color=MINT, bold=True),
              text(0.9, 2.35, 8.6, 1.9, title, size=46, color=WHITE, font=HEAD, title=True),
              text(0.9, 4.35, 7.4, 1.0, subtitle, size=20, color=LIGHT_ON_NAVY))
    x = 0.9
    for chip in chips:
        width = len(chip) * 0.105 + 0.4
        slide.add(Box(x, 5.65, width, 0.4, line=MINT, line_alpha=0.6, radius=0.2, line_w=1),
                  text(x, 5.65, width, 0.4, chip, size=12, color="BFF3EC", align="c", anchor="m"))
        x += width + 0.14
    slide.add(text(0.9, 6.7, 9, 0.3, f"{edition}  ·  Version 1.0  ·  {TODAY}", size=12, color="94ABC6"))
    deck.add(slide, numbered=False)


def section_slide(deck: Deck, number: str, title: str, blurb: str) -> None:
    """A divider slide."""
    slide = Slide()
    dark_background(slide)
    slide.add(text(0.9, 1.7, 4, 1.9, number, size=96, color=MINT, font=HEAD),
              text(0.9, 3.7, 8.2, 1.0, title, size=42, color=WHITE, font=HEAD, title=True),
              text(0.9, 4.75, 7.2, 1.2, blurb, size=19, color=LIGHT_ON_NAVY))
    deck.add(slide, numbered=False)


def content_slide(deck: Deck, kicker: str, title: str, notes: str = "") -> Slide:
    """A white slide with kicker and title at the standard place (added to the deck, returned for drawing)."""
    slide = Slide(notes=notes)
    slide.add(text(0.6, 0.3, 10, 0.3, kicker.upper(), size=11, color=TEAL_D, bold=True),
              text(0.6, 0.58, 12.1, 0.75, title, size=30, color=NAVY, bold=True, font=HEAD, title=True))
    deck.add(slide)
    return slide


def closing_slide(deck: Deck, title: str, lines: list, notes: str = "") -> None:
    """The last slide."""
    slide = Slide(notes=notes)
    dark_background(slide)
    slide.add(text(0.9, 1.6, 8, 1.4, title, size=40, color=WHITE, font=HEAD, title=True))
    body = text(0.9, 3.3, 7.8, 3.2, lines, size=17, color=LIGHT_ON_NAVY, after=10, bullets=True)
    for paragraph in body.paras:
        for run in paragraph.runs:
            if run.font == MONO:
                run.color = MINT  # code on navy needs a light colour
    slide.add(body)
    deck.add(slide, numbered=False)


def part(name: str, box: tuple) -> Path:
    """A cropped piece of a screenshot (saved next to the others) for slides that need a close-up."""
    target = UI / "parts" / f"{Path(name).stem}-{box[1]}-{box[3]}.png"
    target.parent.mkdir(exist_ok=True)
    with Image.open(UI / name) as image:
        image.crop(box).save(target, optimize=True)
    return target


# ------------------------------------------------------------------ building blocks

def card_height(heading: str, body: str, width: float, body_size: float = 14, numbered: bool = False) -> float:
    """Height a card needs for its heading and body."""
    inner = width - 0.44 - (0.0 if not numbered else 0.0)
    head = text_height(heading, 16, inner - (0.55 if numbered else 0), bold=True)
    return 0.2 + max(head, 0.4 if numbered else 0) + 0.12 + text_height(body, body_size, inner, after=4) + 0.25


def card(slide: Slide, x: float, y: float, w: float, h: float, heading: str, body: str, number: str = "", body_size: float = 14,
         fill: str = WHITE, line: str = LINE, head_size: float = 16) -> None:
    """A white card with an optional teal number badge, a heading and a body."""
    slide.add(Box(x, y, w, h, fill=fill, line=line, radius=0.14, shadow=True))
    offset = 0.0
    if number:
        slide.add(Box(x + 0.22, y + 0.2, 0.4, 0.4, fill=TEAL_D, oval=True),
                  text(x + 0.22, y + 0.2, 0.4, 0.4, number, size=14, color=WHITE, bold=True, align="c", anchor="m"))
        offset = 0.55
    head_height = max(text_height(heading, head_size, w - 0.44 - offset, bold=True), 0.4 if number else 0)
    slide.add(text(x + 0.22 + offset, y + 0.2, w - 0.44 - offset, head_height + 0.05, heading, size=head_size, color=NAVY, bold=True, anchor="m" if number else "t"),
              text(x + 0.22, y + 0.2 + head_height + 0.12, w - 0.44, h - head_height - 0.4, body, size=body_size, color=INK, after=4))


def cards_row(slide: Slide, x: float, y: float, w: float, items: list, columns: int, gap: float = 0.3, body_size: float = 14,
              numbered: bool = False, fixed_height: float = 0, fill: str = WHITE) -> float:
    """Lay out cards in a grid with a common row height; returns the bottom edge."""
    width = (w - gap * (columns - 1)) / columns
    rows = [items[i:i + columns] for i in range(0, len(items), columns)]
    cursor = y
    counter = 0
    for row in rows:
        height = fixed_height or max(card_height(h_, b_, width, body_size, numbered) for h_, b_ in row)
        for column, (heading, body) in enumerate(row):
            counter += 1
            card(slide, x + column * (width + gap), cursor, width, height, heading, body, str(counter) if numbered else "", body_size, fill)
        cursor += height + gap
    return cursor - gap


def table(slide: Slide, x: float, y: float, w: float, columns: list, rows: list, size: float = 12.5, first_bold: bool = True,
          pad: float = 0.1, header_size: float = 12) -> float:
    """A table drawn with shapes: columns is [(header, fraction of width)], rows is a list of lists of strings."""
    widths = [w * fraction for _, fraction in columns]
    header_height = 0.44
    heights = []
    for row in rows:
        heights.append(max(text_height(cell, size, (widths[i] - 0.28) / (1.3 if "`" in cell else 1.0), bold=(i == 0 and first_bold)) for i, cell in enumerate(row)) + 2 * pad)
    total = header_height + sum(heights)
    slide.add(Box(x, y, w, total, fill=WHITE, line=LINE, radius=0.1, shadow=True))
    slide.add(Box(x, y, w, header_height, fill=NAVY, radius=0.1), Box(x, y + 0.2, w, header_height - 0.2, fill=NAVY))
    cursor_x = x
    for (header, _), width in zip(columns, widths):
        slide.add(text(cursor_x + 0.14, y, width - 0.28, header_height, header, size=header_size, color=WHITE, bold=True, anchor="m"))
        cursor_x += width
    cursor_y = y + header_height
    for index, (row, height) in enumerate(zip(rows, heights)):
        if index % 2 == 1:
            slide.add(Box(x + 0.01, cursor_y, w - 0.02, height, fill=PAPER))
        cursor_x = x
        for column, (cell, width) in enumerate(zip(row, widths)):
            slide.add(text(cursor_x + 0.14, cursor_y, width - 0.28, height, cell, size=size, color=NAVY if (column == 0 and first_bold) else INK,
                           bold=(column == 0 and first_bold), anchor="m"))
            cursor_x += width
        cursor_y += height
    assert cursor_y <= CONTENT_BOTTOM + 0.05, f"table runs to {cursor_y:.2f} in"
    return cursor_y


def stat_tiles(slide: Slide, x: float, y: float, w: float, h: float, tiles: list, columns: int, gap: float = 0.3) -> None:
    """Big-number tiles: (number, label, detail)."""
    width = (w - gap * (columns - 1)) / columns
    rows = -(-len(tiles) // columns)
    height = (h - gap * (rows - 1)) / rows
    for index, (number, label, detail) in enumerate(tiles):
        tile_x, tile_y = x + (index % columns) * (width + gap), y + (index // columns) * (height + gap)
        slide.add(Box(tile_x, tile_y, width, height, fill=NAVY if index == 0 else WHITE, line=None if index == 0 else LINE, radius=0.16, shadow=True))
        dark = index == 0
        slide.add(text(tile_x + 0.3, tile_y + 0.15, width - 0.6, 0.95, number, size=48, color=MINT if dark else TEAL_D, font=HEAD, bold=True, anchor="m"),
                  text(tile_x + 0.3, tile_y + 1.1, width - 0.6, 0.4, label, size=16, color=WHITE if dark else NAVY, bold=True),
                  text(tile_x + 0.3, tile_y + 1.5, width - 0.6, height - 1.6, detail, size=13, color=LIGHT_ON_NAVY if dark else MUTED))


def step_row(slide: Slide, x: float, y: float, w: float, h: float, steps: list, body_size: float = 13) -> None:
    """Numbered boxes in a row joined by arrows: (heading, body)."""
    gap = 0.4
    width = (w - gap * (len(steps) - 1)) / len(steps)
    for index, (heading, body) in enumerate(steps):
        sx = x + index * (width + gap)
        card(slide, sx, y, width, h, heading, body, str(index + 1), body_size, head_size=15)
        if index < len(steps) - 1:
            slide.add(text(sx + width, y + h / 2 - 0.25, gap, 0.5, "›", size=30, color=TEAL_D, bold=True, align="c", anchor="m"))


def callout(slide: Slide, x: float, y: float, w: float, h: float, heading: str, body: str, size: float = 14) -> None:
    """A tinted box with a bold heading, used for 'what it proves' notes."""
    slide.add(Box(x, y, w, h, fill=TEAL_SOFT, line="9ED8D1", radius=0.14),
              text(x + 0.22, y + 0.16, w - 0.44, 0.3, heading, size=13, color=TEAL_D, bold=True),
              text(x + 0.22, y + 0.5, w - 0.44, h - 0.6, body, size=size, color=INK, after=4))


def picture_card(slide: Slide, x: float, y: float, w: float, h: float, path: Path, alt: str, pad: float = 0.12) -> None:
    """A white frame with a picture fitted inside."""
    slide.add(Box(x, y, w, h, fill=WHITE, line=LINE, radius=0.12, shadow=True), fit(str(path), x + pad, y + pad, w - 2 * pad, h - 2 * pad, alt))


def diagram_slide(deck: Deck, kicker: str, title: str, name: str, alt: str, side: list = None, below: list = None, notes: str = "") -> None:
    """A diagram picture, full width, with bullet points beside it (``side``) or under it (``below``)."""
    slide = content_slide(deck, kicker, title, notes)
    path = DIAGRAMS / f"{name}.png"
    width, height = Image.open(path).size
    if side:
        picture_card(slide, 0.6, 1.5, 8.5, 5.3, path, alt)
        slide.add(text(9.4, 1.55, 3.35, 5.2, side, size=14, color=INK, after=9, bullets=True))
        return
    card_h = min(5.3, 12.13 * height / width + 0.28)
    picture_card(slide, 0.6, 1.5, 12.13, card_h, path, alt)
    if below:
        slide.add(text(0.6, 1.5 + card_h + 0.25, 12.13, 6.9 - (1.5 + card_h + 0.25), below, size=14, color=INK, after=6, bullets=True))


def shot_slide(deck: Deck, kicker: str, title: str, picture: str, signed_in: str, sees: list, proves: str, notes: str = "") -> None:
    """A screenshot on the left, what you see and what it proves on the right."""
    slide = content_slide(deck, kicker, title, notes)
    with Image.open(UI / picture) as image:
        shown_h = min(5.06, 7.46 * image.height / image.width)
    frame_h = shown_h + 0.24
    picture_card(slide, 0.6, 1.5 + (5.3 - frame_h) / 2, 7.7, frame_h, UI / picture, title)
    if signed_in:
        slide.add(Box(8.6, 1.5, 4.13, 0.38, fill=TEAL_SOFT, radius=0.19), text(8.6, 1.5, 4.13, 0.38, signed_in, size=12.5, color=TEAL_D, bold=True, align="c", anchor="m"))
    slide.add(text(8.6, 2.05, 4.13, 0.3, "What you see", size=15, color=NAVY, bold=True),
              text(8.6, 2.42, 4.13, 2.5, sees, size=13.5, color=INK, after=6, bullets=True))
    callout(slide, 8.6, 4.95, 4.13, 1.85, "What it proves", proves, size=13.5)


def terminal_slide(deck: Deck, kicker: str, title: str, picture: str, command: str, points: list, notes: str = "") -> None:
    """A command, its terminal output on a dark panel, and cards that explain it."""
    slide = content_slide(deck, kicker, title, notes)
    slide.add(Box(0.6, 1.5, 12.13, 0.46, fill=TEAL_SOFT, radius=0.23),
              text(0.85, 1.5, 11.6, 0.46, f"`{command}`", size=13, anchor="m"))
    width, height = Image.open(UI / picture).size
    panel_h = min(3.0, 11.6 * height / width + 0.5)
    slide.add(Box(0.6, 2.15, 12.13, panel_h, fill="0C0C0C", radius=0.14, shadow=True),
              fit(str(UI / picture), 0.85, 2.3, 11.6, panel_h - 0.3, title))
    cards_row(slide, 0.6, 2.15 + panel_h + 0.3, 12.13, points, len(points), body_size=13.5)


def bars(slide: Slide, x: float, y: float, w: float, rows: list, bar_h: float = 0.46, gap: float = 0.42) -> None:
    """Horizontal progress bars: (label, detail, value 0-100, colour)."""
    track_x, track_w = x + 2.9, w - 2.9
    for index, (label, detail, value, color) in enumerate(rows):
        row_y = y + index * (bar_h + gap)
        slide.add(text(x, row_y - 0.04, 2.8, 0.35, label, size=15, color=NAVY, bold=True),
                  text(x, row_y + 0.3, 2.8, 0.3, detail, size=12, color=MUTED),
                  Box(track_x, row_y, track_w, bar_h, fill=PAPER, line=LINE, radius=0.12),
                  Box(track_x, row_y, max(track_w * value / 100, 0.3), bar_h, fill=color, radius=0.12),
                  text(track_x + 0.2, row_y, track_w - 0.4, bar_h, f"{value:g}%", size=18, color=WHITE, bold=True, anchor="m"))


# ------------------------------------------------------------------ deck 1: reviewer walkthrough

def reviewer_deck() -> Deck:
    """The whole project for a reviewer."""
    deck = Deck("Invoice Approval: reviewer walkthrough", "Approval limits by role, built and verified with AI in the software lifecycle")
    title_slide(deck, "Reviewer walkthrough", "Invoice Approval:\napproval limits by role",
                "One feature, taken from specification to a reviewed pull request, with the evidence around it.",
                ["Python  ·  FastAPI", "Spec Kit", "Claude Code", "pytest", "mutmut", "Playwright"],
                "Start here. This deck explains the whole project in five parts: the feature, the architecture, how AI was used, the proof, and how to check it yourself.")

    slide = content_slide(deck, "Overview", "The assignment, and what was delivered")
    bottom = cards_row(slide, 0.6, 1.55, 12.13, [
        ("The ask", "Add **role-based approval limits** to a small invoice approval service, and take it from specification to a reviewed pull request with the evidence around it: tests, mutation scores, a browser test, a review with a verdict on every finding, and a log of every AI interaction."),
        ("The feature", "A **Manager** may approve up to 50,000.00. A **Director** may approve up to 500,000.00. Above that, **two different approvers** are needed and the second must be a Director. A refused attempt returns a **clear reason** and changes **nothing**."),
        ("The outcome", "**177** unit tests and **1** browser test pass. Mutation score rose from **63.9%** to **100%**. **11** review findings each have a verdict. Every AI interaction is logged with **27** fixed keys."),
    ], 3, body_size=14.5)
    slide.add(text(0.6, bottom + 0.4, 12.13, 0.6, "Stack:  Python 3.13  ·  FastAPI  ·  pytest  ·  mutmut 3.8  ·  Playwright  ·  Spec Kit  ·  Claude Code (Sonnet 5.5)", size=14, color=MUTED, align="c"))
    slide.add(text(0.6, bottom + 0.9, 12.13, 0.8,
                   "The original demo is ASP.NET Core. With no .NET SDK available and Python as the requirement, the backend was ported to FastAPI with the same layering, endpoints and web UI, and the 7 original tests were kept green before any feature work.",
                   size=13, color=MUTED, align="c"))
    slide.notes = "State the three things: the ask, the feature, the outcome. Mention the port from C# to Python once and move on."

    slide = content_slide(deck, "Overview", "Results at a glance", "Every number on this slide can be re-run; the commands are on the 'Check it yourself' slide.")
    stat_tiles(slide, 0.6, 1.55, 12.13, 5.1, [
        ("177", "Backend tests pass", "63 policy, 62 service, 36 API, 16 repository contract"),
        ("100%", "Mutation score", "132 of 132 mutants killed; the baseline was 63.9% (23 of 36)"),
        ("1", "Browser test passes", "Manager is refused on an over-limit invoice, the reason is shown, the invoice stays pending"),
        ("11", "Review findings", "6 fixed, 3 dismissed with a reason, 2 deferred and tracked"),
        ("27", "Keys on every log line", "Prompt, tools, sub-agents, AI suggestion, human decision, verification, status"),
        ("5", "Project agents", "spec-writer, implementer, test-reviewer, pr-reviewer, mutation-analyst"),
    ], 3)

    section_slide(deck, "01", "The feature", "What the rules are, the decisions behind them, and the life of an invoice.")

    diagram_slide(deck, "The feature", "Who may approve what", "04-approval-bands", "Approval bands and the role matrix",
                  notes="Read the three bands left to right. The dashed lines are the two limits; the cent either side is tested. Then the table: Manager first approver only above 500,000; Director any; Admin never.")

    slide = content_slide(deck, "The feature", "Decisions made, and why", "These are the specification's clarifications; each became a test.")
    cards_row(slide, 0.6, 1.5, 12.13, [
        ("Limits are inclusive", "50,000.00 is allowed for a Manager; 50,000.01 needs a Director. Same at 500,000. Tests try one cent either side."),
        ("First approver above 500,000", "A Manager or a Director. Only the second approver is constrained: it must be a Director."),
        ("\"The same user\"", "The same account after trimming spaces and ignoring case, so `Dir.One` and ` dir.one ` are one person."),
        ("Admin cannot approve", "Admin keeps reject and delete, never approval. The old Approver role became Manager."),
        ("A refusal is not a Reject", "\"Rejected attempt\" means an approval the rules refuse: 403 with a reason, nothing written. The Reject button is unchanged."),
        ("Nothing changes on refusal", "Every check runs before the first change, so there is no half-done state to clean up."),
    ], 3, body_size=13.5, numbered=True)

    diagram_slide(deck, "The feature", "The life of an invoice", "05-invoice-lifecycle", "Invoice states and transitions",
                  notes="Draft, Pending, then Approved or Rejected. A refused approval is not a transition. Only the final approval sets decided_by and decided_at.")

    section_slide(deck, "02", "Architecture", "Where each responsibility lives, how one request flows, and the design principles behind it.")

    diagram_slide(deck, "Architecture", "System architecture", "01-architecture-overview", "Layered architecture of the application",
                  notes="Top to bottom: the browser, the web layer, the domain. The domain has no web or storage code. create_app is the only place that chooses concrete classes.")

    diagram_slide(deck, "Architecture", "One approval request: the checks", "02a-approve-sequence-steps", "Sequence of an approve request, steps 1 to 6",
                  below=["The session is checked first (401), then the role (403), then the service takes a lock, loads the invoice (404, 409) and asks the policy."],
                  notes="Follow the numbered steps down. Nothing has been changed yet at this point.")

    diagram_slide(deck, "Architecture", "One approval request: refused or allowed", "02b-approve-sequence-outcomes", "Sequence of an approve request, outcomes",
                  notes="The red box is the refusal path: the exception is raised before anything is written. The green box is the success path.")

    diagram_slide(deck, "Architecture", "The approval rules: three gates", "03a-approval-gates", "Gates of the approval rules",
                  below=["Rules run in a **fixed order**: state, role, Manager limit, same user, second must be a Director.",
                         "The **first objection wins** and its text is the reason shown to the user.",
                         "Each red box is a real message from the code and is asserted word for word in a test."],
                  notes="The same flow as the code in approval_policy.py. Each rule is its own small class.")

    diagram_slide(deck, "Architecture", "The approval rules: one approver or two", "03b-approval-branches", "Branches of the approval rules",
                  notes="Above 500,000 the same-user and second-must-be-a-Director rules apply; up to 500,000 only the Manager limit does.")

    slide = content_slide(deck, "Architecture", "Design: the SOLID principles, with proof", "Detail: docs/guides/19-solid-design.md")
    table(slide, 0.6, 1.5, 12.13, [("Principle", 0.15), ("What changed", 0.5), ("Proof", 0.35)], [
        ["Single responsibility", "main.py was split into wiring, error mapping and the session check; each approval rule is its own class.", "Each file has one job; every rule class has its own tests."],
        ["Open / closed", "Four rule classes plus an ApprovalPolicy that asks them in order; limits are data. A new rule is a new class.", "`test_a_new_rule_plugs_into_the_policy_without_changing_the_existing_rules`"],
        ["Liskov substitution", "One contract test suite runs against the fake repository and the real one.", "`test_repository_contract.py` (16 tests)"],
        ["Interface segregation", "The approval service needs two operations, so it takes an ApprovalStore, not the six-method repository.", "`test_the_service_works_with_a_store_that_offers_only_find_and_save`"],
        ["Dependency inversion", "The service takes a policy and a clock as arguments; login uses a UserDirectory; create_app accepts replacements.", "Tests inject a stub policy, a fixed clock and a one-user directory."],
    ], size=14, pad=0.13)
    slide.add(text(0.6, 6.5, 12.13, 0.35, "Behaviour did not change: all 134 earlier tests passed unchanged, 43 were added, and mutation stayed at 100%.", size=13, color=MUTED))

    slide = content_slide(deck, "Architecture", "Key design decisions", "Full table: docs/guides/03-architecture-and-design.md")
    table(slide, 0.6, 1.5, 12.13, [("Decision", 0.2), ("Choice", 0.33), ("Why", 0.47)], [
        ["Money", "`Decimal`, never float", "Exact comparison at 50,000.00 and 50,000.01."],
        ["Refusal signal", "`ApprovalNotPermittedError` mapped to 403", "Distinct from 409 (wrong state), 404 and 400 (bad input)."],
        ["No partial writes", "Check first, then change", "The in-memory repository returns the live object, so changing first would leak state."],
        ["Atomic approvals", "One lock in `ApprovalService`", "Two clicks by one user could both pass the duplicate check (finding F1)."],
        ["Same user", "`strip().casefold()`", "Stops `Dir.One` versus ` dir.one ` slipping through."],
        ["Amount input", "`gt=0, max_digits=14, decimal_places=2`", "Rejects `1e999999`, NaN and sub-cent values (findings F2, F3)."],
        ["Unexpected errors", "500 with no detail", "Only `DomainValidationError` maps to 400 (finding F5)."],
    ], size=14, pad=0.13)

    section_slide(deck, "03", "Built with AI, in the open", "The context file, agents, skills, hooks, the specification and the commit plan, and how each one shows up as evidence.")

    diagram_slide(deck, "AI in the lifecycle", "The workflow, from context to reviewed PR", "06a-ai-pipeline", "Seven steps of the AI workflow",
                  below=["Each step leaves evidence in the repository: rules, specification, code and tests, stronger tests, scores, a browser test, a reviewed PR.",
                         "Agents are read-only wherever they judge work (test-reviewer, pr-reviewer, mutation-analyst); only spec-writer and implementer may write."],
                  notes="The seven steps left to right, with the output of each underneath.")

    diagram_slide(deck, "AI in the lifecycle", "Hooks write the log; agents do the work", "06b-ai-automation", "Hooks and agents",
                  notes="Hooks run automatically on every event and write the log. The lower lane lists the five agents.")

    slide = content_slide(deck, "AI in the lifecycle", "Context matters: AGENTS.md", "Experiment details: ASSIGNMENT.md section 7")
    cards_row(slide, 0.6, 1.5, 6.0, [
        ("What AGENTS.md holds", "The approval rules table with inclusive limits; layering (rules only in `domain/`); the exact commands for tests, mutation and the browser test; review expectations (one verdict per finding); a Never list."),
        ("Why a file, not a prompt", "It is read at the start of every session and by every sub-agent, so each step starts from the same rules without repeating them."),
    ], 1, body_size=14)
    slide.add(text(6.95, 1.5, 5.8, 0.35, "Same prompt, two agents", size=15, color=NAVY, bold=True))
    table(slide, 6.95, 1.95, 5.78, [("Aspect", 0.24), ("Without", 0.38), ("With AGENTS.md", 0.38)], [
        ["Boundaries", "Whole units: 49,999 / 50,001", "One cent: 50,000.00 / .01"],
        ["Same user", "Same name only", "Trimmed, case-folded"],
        ["Admin", "Not mentioned", "Never approves"],
        ["Test command", "\"Find it in the build files\"", "The real commands"],
        ["Findings", "Fix, decline or ask", "Fixed, dismissed or deferred"],
    ], size=13.5, pad=0.12)
    slide.add(text(6.95, 6.2, 5.78, 0.6, "One run per arm, and AGENTS.md contains part of the answer by design: read it as an illustration, not a benchmark.", size=11.5, color=MUTED, italic=True))

    slide = content_slide(deck, "AI in the lifecycle", "Agents and skills, and what each one caught", "Files: .claude/agents and .claude/skills")
    table(slide, 0.6, 1.5, 12.13, [("Role", 0.17), ("Access", 0.15), ("Job", 0.3), ("What it produced here", 0.38)], [
        ["spec-writer", "read, write", "Writes Spec Kit files only", "Spec with 7 clarifications, plan, research, data model, contract, 25 tasks"],
        ["implementer", "read, write, shell", "One task group at a time, tests first", "Single-approver limits, then the two-approver rule"],
        ["test-reviewer", "read-only", "Finds tests that cannot fail", "Weak state tests, 2 duplicates, a fake that hid missing saves, 14 missing cases"],
        ["mutation-analyst", "read-only", "Classifies surviving mutants", "16 survivors, all missing tests (none equivalent); the tests to add"],
        ["pr-reviewer", "read-only", "Answers only in the findings JSON format", "11 findings, two reproduced against the running code"],
        ["Skills", "loaded on demand", "approval-rules, review-findings, run-checks", "One source for the rules, the verdict vocabulary and the exact check commands"],
    ], size=13.5, pad=0.12)

    slide = content_slide(deck, "AI in the lifecycle", "Hooks and the interaction log", "Detail: docs/guides/10-ai-workflow-guide.md")
    cards_row(slide, 0.6, 1.5, 12.13, [
        ("log_event.py", "Runs on prompt, tool use, sub-agent stop and session stop. Appends **one JSON line** with 27 fixed keys. Redacts secrets, local paths and the account name."),
        ("check_summary.py", "Runs after shell commands. Turns pytest, mutmut and Playwright output into `CHECK name | metrics | result=pass/fail` so every run is comparable."),
        ("validate_review.py", "Runs when a sub-agent stops. **Blocks** a `pr-reviewer` answer that is not the findings JSON schema."),
    ], 3, body_size=13.5)
    slide.add(Box(0.6, 3.95, 12.13, 2.8, fill=NAVY, radius=0.14, shadow=True),
              text(0.9, 4.1, 11.5, 0.3, "The 27 keys of every line in logs/ai-interactions.jsonl", size=13, color=MINT, bold=True),
              text(0.9, 4.5, 11.5, 1.5, "id, timestamp, session, stage, event, agent, agent_name, agent_type, ai_tool, model, mode, related_ids, parent_task, context, request, summary, skills_used, subagents_used, mcp_tools_used, tools_used, suggestion, human_decision, action_verification, limitation, status, artifacts, source",
                   size=13, color="D7F5F0", font=MONO),
              text(0.9, 5.85, 11.5, 0.8, "A prompt gets an id; every later action carries it in **parent_task**, so each edit, command and check traces back to the request that caused it. **python scripts/summarize_log.py** validates every line and writes the readable summary.",
                   size=13, color=LIGHT_ON_NAVY))

    slide = content_slide(deck, "AI in the lifecycle", "Spec Kit: the specification comes first", "Files: specs/001-invoice-approval-limits/ and .specify/")
    step_row(slide, 0.6, 1.5, 12.13, 2.75, [
        ("Constitution", "6 principles: rules in the domain, test-first with negative cases, boundaries both sides, refusals explain themselves."),
        ("Specify", "3 user stories with acceptance scenarios and the exact feature text."),
        ("Clarify", "7 questions answered in writing: inclusive limits, first approver, same user, Admin."),
        ("Plan", "Plan, research, data model and the approvals API contract."),
        ("Tasks", "T001 to T025 in 5 phases; tests before code for each story."),
    ], body_size=12.5)
    slide.add(text(0.6, 4.45, 12.13, 0.3, "What is in the folder", size=15, color=NAVY, bold=True),
              text(0.6, 4.85, 12.13, 0.9, ["`spec.md`   `plan.md`   `research.md`   `data-model.md`   `quickstart.md`   `tasks.md`",
                                          "`contracts/approvals-api.md`   `checklists/requirements.md`   `.specify/memory/constitution.md`"],
                   size=13.5, after=6))
    callout(slide, 0.6, 5.75, 12.13, 1.1, "Honest note", "Spec Kit was installed with `specify init`; the spec, plan and tasks follow its templates and were written by the assistant directly rather than by running the `/speckit-*` commands one by one.", size=13)

    slide = content_slide(deck, "AI in the lifecycle", "Built in small steps: the commit plan", "Source: ASSIGNMENT.md section 5")
    table(slide, 0.6, 1.5, 12.13, [("#", 0.05), ("Commit", 0.5), ("Why it stands alone", 0.45)], [
        ["1", "Port backend from ASP.NET Core to Python/FastAPI (behaviour-identical)", "No .NET SDK; keeps the 7 original tests green before any feature"],
        ["2", "Add AGENTS.md rules, skills, sub-agents and AI-interaction logging hooks", "The context every later step relies on"],
        ["3", "Add Spec Kit specification, plan and tasks for approval limits", "The agreed behaviour, before code"],
        ["4", "Enforce Manager and Director approval limits", "Single-approver rules, tests first"],
        ["5", "Require two distinct approvers, second a Director, above 500,000", "Approvals list, duplicate-user and second-approver rules"],
        ["6", "Add Playwright test for a refused over-limit approval and approval progress in the UI", "The browser-level proof"],
        ["7", "Fix PR review findings", "Atomic approvals, amount validation, narrower 400 mapping, strict tests"],
    ], size=13.5, first_bold=False, pad=0.12)

    section_slide(deck, "04", "Proof that it works", "Test layers, the two negative rules, mutation scores, the browser test and the pull-request review.")

    diagram_slide(deck, "Proof", "The test layers", "07-test-layers", "Test pyramid and totals",
                  notes="Policy tests at the base, API tests above, one browser test at the top. Mutation testing judges the unit tests; hook tests protect the logger.")

    slide = content_slide(deck, "Proof", "The two negative rules, tested properly", "Command: python -m pytest backend/tests/test_approval_policy.py -v -k \"same_user or second_approver\"")
    cards_row(slide, 0.6, 1.5, 12.13, [
        ("Same user twice is refused", "Including `Dir.One` versus ` dir.one `, with the duplicate on the new or the stored side."),
        ("A Manager cannot be the second approver", "Above 500,000 a Manager may only be first; a Director must give the second approval."),
        ("A refusal changes nothing", "Each test compares a deep copy before and after, asserts the exact reason text, and checks the repository saw no update."),
    ], 3, body_size=13.5)
    slide.add(Box(0.6, 3.85, 12.13, 2.95, fill="0C0C0C", radius=0.14, shadow=True), fit(str(UI / "21-negative-rules-tests.png"), 0.8, 4.0, 11.73, 2.65, "12 negative-rule tests passed"))

    slide = content_slide(deck, "Proof", "Mutation testing: from 63.9% to 100%", "Tool: mutmut 3.8 on the domain package (WSL). Reports: docs/mutation/")
    bars(slide, 0.6, 1.65, 7.4, [
        ("Baseline", "ported code, 7 tests: 23 of 36", 63.9, "C0504A"),
        ("First pass", "feature + 75 tests: 69 of 85", 81.2, "D49A1A"),
        ("After", "134 tests: 86 of 86", 100, TEAL_D),
        ("After SOLID refactor", "132 of 132", 100, TEAL),
    ])
    slide.add(Box(8.3, 1.55, 4.43, 3.2, fill=NAVY, radius=0.14, shadow=True),
              text(8.6, 1.7, 3.9, 0.3, "Final mutation run", size=13, color=MINT, bold=True),
              text(8.6, 2.05, 3.9, 1.1, "132 / 132", size=50, color=WHITE, font=HEAD, bold=True, anchor="m"),
              text(8.6, 3.2, 3.9, 1.4, ["Killed: 132   Survived: 0", "Timeout: 0   Other: 0", "Mutation score: **100.0%**"], size=14, color="D7F5F0", font=MONO, after=4))
    slide.add(text(8.3, 5.0, 4.43, 1.85, ["**16 survivors** after the first pass were all missing tests: a fake that never saved, unasserted timestamps and messages.",
                                          "The refactor left one survivor (99.2%): a `>` that an earlier rule had been hiding. A boundary test per rule closed it."],
                   size=12.5, after=6, bullets=True))
    slide.add(text(0.6, 5.1, 7.4, 1.75, ["The mutant count rises from 36 to 132 because the scope grew (new rule files), so compare the **kill rate**, not the counts.",
                                        "Mutation testing measured the **domain unit tests** only; the API tests are not in the run.",
                                        "A mutant that survives means a change to the code went unnoticed by every test."],
                   size=12.5, color=MUTED, after=6, bullets=True))

    slide = content_slide(deck, "Proof", "Browser test: one refusal, end to end", "Command: cd e2e && npx playwright test --headed")
    slide.add(Box(0.6, 1.5, 12.13, 0.46, fill=TEAL_SOFT, radius=0.23), text(0.85, 1.5, 11.6, 0.46, "`cd e2e; npx playwright test --headed; cd ..`", size=13, anchor="m"))
    slide.add(Box(0.6, 2.15, 12.13, 1.5, fill="0C0C0C", radius=0.14, shadow=True), fit(str(UI / "23-playwright-one-passed.png"), 0.8, 2.25, 11.73, 1.3, "Playwright: 1 passed"))
    cards_row(slide, 0.6, 3.95, 7.6, [
        ("What the test does", "Signs in as `demo.manager`, **creates its own** 75,000.00 invoice, submits it, presses Approve on the Approvals tab, and expects the exact text **A Manager may approve invoices up to 50,000.00; this invoice is 75,000.00 and needs a Director.** The invoice must stay Pending Approval in both the list and the table. It then deletes the invoice, so the server is left as it was."),
    ], 1, body_size=13)
    cards_row(slide, 8.5, 3.95, 4.23, [
        ("How it is written", "Page objects (`LoginPage`, `InvoicesPage`, `ApprovalsPage`) and role-based locators (`getByRole`, `getByLabel`); no CSS or XPath selectors."),
    ], 1, body_size=13, fixed_height=2.8)

    slide = content_slide(deck, "Proof", "Reviewing the PR: 11 findings, each with a verdict", "Full table with reasons: docs/pr-review.md")
    for index, (number, label, color) in enumerate([("6", "fixed", TEAL_D), ("3", "dismissed", MUTED), ("2", "deferred", AMBER)]):
        y = 1.5 + index * 1.75
        slide.add(Box(0.6, y, 2.6, 1.55, fill=WHITE, line=LINE, radius=0.14, shadow=True),
                  text(0.6, y + 0.05, 2.6, 1.0, number, size=54, color=color, font=HEAD, bold=True, align="c", anchor="m"),
                  text(0.6, y + 1.0, 2.6, 0.4, label, size=16, color=NAVY, bold=True, align="c"))
    table(slide, 3.5, 1.5, 9.23, [("Finding", 0.4), ("Verdict", 0.14), ("How it was settled", 0.46)], [
        ["F1 (high) approvals not atomic", "fixed", "Lock around submit/approve/reject; threaded tests fail without it"],
        ["F2 (high) `1e999999` breaks the list", "fixed", "Amount validated at the API; invalid input never stored"],
        ["F4 `float()` loses precision", "dismissed", "Input now bounded; every limit round-trips exactly to the cent"],
        ["F9 roles matched exactly", "dismissed", "Roles come from the server; failing closed is intended and pinned by a test"],
        ["F7 no two-Director UI test", "deferred", "Tracked as T024; the flow is covered at API level"],
        ["F11 tokens never expire", "deferred", "Pre-existing demo auth; tracked as T025"],
    ], size=12, first_bold=False, pad=0.09)
    slide.add(text(3.5, 5.95, 9.23, 0.8, "The `test-reviewer` pass raised 14 further gaps in the tests themselves; all were acted on or consciously declined (see the report).", size=12.5, color=MUTED))

    slide = content_slide(deck, "Proof", "The application in action")
    for index, (picture, caption) in enumerate([
        (UI / "06-manager-refused-over-limit.png", "A Manager is refused above 50,000.00, with the reason"),
        (part("08-same-director-refused.png", (0, 640, 1234, 1028)), "The same Director cannot approve twice above 500,000.00"),
        (UI / "13-admin-cannot-approve.png", "Admin may look, but can never approve"),
        (part("14-rejection-reasons-shown.png", (0, 330, 1234, 760)), "A rejection shows who rejected it and why"),
    ]):
        x, y = 0.6 + (index % 2) * 6.17, 1.45 + (index // 2) * 2.7
        slide.add(Box(x, y, 5.96, 2.45, fill=WHITE, line=LINE, radius=0.12, shadow=True), fit(str(picture), x + 0.1, y + 0.1, 5.76, 1.95, caption),
                  text(x + 0.15, y + 2.07, 5.66, 0.34, caption, size=12.5, color=NAVY, bold=True, align="c"))
    slide.add(text(0.6, 6.85, 12.13, 0.2, "", size=2))

    section_slide(deck, "05", "For the reviewer", "Where every hand-in item lives, how to check it yourself in minutes, and what is honestly left open.")

    slide = content_slide(deck, "For the reviewer", "Hand-in checklist: where each item is", "Details: docs/guides/16-submission-checklist.md")
    table(slide, 0.6, 1.5, 12.13, [("#", 0.04), ("Item", 0.3), ("Where to look", 0.46), ("Status", 0.2)], [
        ["1", "Pull request, 3 or more standalone commits", "Commit plan in `ASSIGNMENT.md` section 5 (7 commits)", "Made by the author"],
        ["2", "Updated AGENTS.md", "`AGENTS.md`; imported by `CLAUDE.md`", "In the repository"],
        ["3", "Spec files", "`specs/001-invoice-approval-limits/`, `.specify/`", "In the repository"],
        ["4", "Unit tests incl. both negative rules", "`backend/tests/` (177 tests)", "Passing"],
        ["5", "One Playwright test: rejected over-limit approval", "`e2e/tests/over-limit-rejection.spec.ts`", "Passing"],
        ["6", "Mutation scores before and after, as text", "`ASSIGNMENT.md` section 3; `docs/mutation/*.txt`", "63.9% to 100%"],
        ["7", "PR description with a verdict on every finding", "`docs/pr-review.md` (11 findings)", "Ready to paste"],
        ["8", "Log of all AI interaction", "`logs/ai-interactions.jsonl` and its summary", "Validated"],
        ["9", "ASSIGNMENT.md with write-up and video link", "`ASSIGNMENT.md`", "Link added after recording"],
        ["10", "8 to 10 minute demo video", "Recorded and linked by the author", "Made by the author"],
    ], size=13, first_bold=False, pad=0.085)

    slide = content_slide(deck, "For the reviewer", "Check it yourself in five minutes", "Windows PowerShell; the mutation run needs WSL (Ubuntu).")
    rows = [
        ("Install", "pip install -e \"backend[dev]\"", "once"),
        ("Unit tests", "python -m pytest backend/tests -q", "177 passed"),
        ("Run the app", "python -m uvicorn invoice_app.api.main:app --app-dir backend/src --port 5000", "http://localhost:5000"),
        ("Browser test", "cd e2e; npm install; npx playwright install chromium; npm test", "1 passed"),
        ("Mutation", "wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh check", "100.0% in about 13 s"),
        ("AI log", "python scripts/summarize_log.py", "validates every line"),
    ]
    for index, (label, command, result) in enumerate(rows):
        y = 1.55 + index * 0.84
        slide.add(Box(0.6, y, 12.13, 0.7, fill=WHITE, line=LINE, radius=0.12, shadow=True),
                  Box(0.78, y + 0.14, 0.42, 0.42, fill=TEAL_D, oval=True),
                  text(0.78, y + 0.14, 0.42, 0.42, str(index + 1), size=14, color=WHITE, bold=True, align="c", anchor="m"),
                  text(1.4, y, 1.6, 0.7, label, size=15, color=NAVY, bold=True, anchor="m"),
                  Box(3.0, y + 0.12, 6.75, 0.46, fill=PAPER, radius=0.08),
                  text(3.12, y + 0.12, 6.55, 0.46, f"`{command}`", size=11.5, anchor="m"),
                  text(9.95, y, 2.65, 0.7, result, size=13, color=TEAL_D, bold=True, anchor="m"))
    slide.add(text(0.6, 6.65, 12.13, 0.3, "Demo accounts (local only): demo.manager, demo.director, demo.director2, demo.admin. Password ChangeMe123!. Try INV-2001 (75,000.00) and INV-2002 (600,000.00).", size=12, color=MUTED))

    slide = content_slide(deck, "For the reviewer", "Honest limits and what is still open")
    cards_row(slide, 0.6, 1.5, 6.0, [
        ("Limits of the evidence", "Mutation testing covered the **domain unit tests** only. The AGENTS.md experiment was **one run per arm**. Early planning and the port were logged as `reconstructed`, not captured live. Sub-agents ran as general-purpose agents reading the agent files in the session that created them."),
        ("Not production", "Sign-in is a **demo**: in-memory sessions, no expiry, no throttling. The store is in memory. Both are documented and outside this feature."),
    ], 1, body_size=13.5, gap=0.3)
    cards_row(slide, 6.73, 1.5, 6.0, [
        ("Deferred, with tracking", "**T024** a second Playwright spec for the two-Director flow, with a reset endpoint so UI tests that change data are repeatable. **T025** session expiry and constant-time password comparison."),
        ("Left to the author", "Create the pull request from the commit plan, record and link the 8 to 10 minute video, and paste the link into `ASSIGNMENT.md`."),
    ], 1, body_size=13.5, gap=0.3)

    closing_slide(deck, "Everything here can be re-run", [
        "Documentation: 23 PDF documents in `docs/pdf/`",
        "Slides: `docs/presentations/` (this deck and the UI walkthrough)",
        "Rules of record: `specs/001-invoice-approval-limits/spec.md`",
        "Evidence: `ASSIGNMENT.md`, `docs/pr-review.md`, `docs/mutation/`, `logs/`",
    ], "Close by pointing at the five folders. Invite the reviewer to run the unit tests first.")
    return deck


# ------------------------------------------------------------------ deck 2: UI walkthrough

def ui_deck() -> Deck:
    """The running application, screen by screen."""
    deck = Deck("Invoice Approval: the application, screen by screen", "Every screen of the running application and the rule it proves")
    title_slide(deck, "User interface walkthrough", "The application,\nscreen by screen",
                "Real screenshots of the running app: what each screen shows and which rule it proves.",
                ["Sign-in", "Invoices", "Approvals", "Refusals", "Evidence"],
                "This deck follows one realistic session: sign in, look at the invoices, try to approve, get refused, and finish an approval.",
                edition="Screen-by-screen edition")

    slide = content_slide(deck, "Before you start", "Four accounts, three roles")
    table(slide, 0.6, 1.5, 12.13, [("Account", 0.2), ("Role", 0.14), ("Can approve", 0.36), ("Also can", 0.3)], [
        ["demo.manager", "Manager", "Invoices up to 50,000.00", "Create, submit, reject"],
        ["demo.director", "Director", "Up to 500,000.00 alone; above that as first or second approver", "Create, submit, reject"],
        ["demo.director2", "Director", "The same as demo.director: a second, different person", "Create, submit, reject"],
        ["demo.admin", "Admin", "Nothing: Admin never approves", "Create, submit, reject, delete"],
    ], size=13.5, pad=0.14)
    slide.add(text(0.6, 4.55, 12.13, 0.35, "Password for all four: `ChangeMe123!` (local demo only).", size=14, color=MUTED))
    cards_row(slide, 0.6, 5.1, 12.13, [
        ("INV-2001  ·  75,000.00", "Needs one Director. A Manager is refused."),
        ("INV-2002  ·  600,000.00", "Needs two different approvers, the second a Director."),
    ], 2, body_size=13.5, fixed_height=1.45)

    shot_slide(deck, "Sign-in", "The sign-in screen", "01-sign-in.png", "Not signed in",
               ["Only a sign-in card is shown; there is **no Sign out button** and no invoice data.",
                "Every part of the app is behind sign-in: the server answers 401 to anything else.",
                "Username and password; one button."],
               "Nothing is visible before sign-in, and the page does not pretend you are signed in (a bug where Sign out showed here was found and fixed).",
               "The first screen. Point out there is no Sign out button and no data.")

    shot_slide(deck, "Sign-in", "A wrong password is refused", "02-invalid-sign-in.png", "Not signed in",
               ["The message **Invalid username or password.** appears in a red notice under the button.",
                "It does not say which of the two was wrong.",
                "The password field is masked."],
               "Sign-in failures are generic by design, so the form cannot be used to find out which usernames exist.")

    shot_slide(deck, "Invoices", "The Invoices tab", "03-invoices-seed-data.png", "Signed in as demo.manager (Manager)",
               ["A **New invoice** form (customer name, amount) and the **All invoices** table.",
                "Status pills: **Pending Approval** (amber), **Approved** (teal), **Draft** (grey), **Rejected** (red).",
                "A Draft invoice has a **Submit for approval** button.",
                "INV-2001 (75,000.00) and INV-2002 (600,000.00) are the invoices built to try the rules."],
               "The seed data covers every status, so each rule can be tried without creating anything first.")

    shot_slide(deck, "Approvals", "Rejecting needs a reason", "04-reject-reason-typed.png", "Signed in as demo.manager (Manager)",
               ["The **Approvals** tab lists every invoice waiting for a decision.",
                "Each card has **Approve**, a reason box and **Reject**.",
                "A reason has been typed for INV-1002.",
                "INV-2002 shows **0 of 2 approvals**: it needs two people."],
               "Reject is a different action from a refused approval: it ends the invoice, and it requires a reason that is stored and shown later.")

    shot_slide(deck, "Approvals", "Reject without a reason is refused", "05-reason-required.png", "Signed in as demo.director2 (Director)",
               ["Reject was pressed with the reason box empty.",
                "A red notice says **A reason is required to reject an invoice.**",
                "INV-1004 is still in the list: nothing was changed."],
               "A missing reason is bad input (HTTP 400). It is caught before the invoice is touched.")

    shot_slide(deck, "The rules", "A Manager is refused above 50,000.00", "06-manager-refused-over-limit.png", "Signed in as demo.manager (Manager)",
               ["Approve was pressed on INV-1006, **500,000.00**.",
                "The reason is shown in full: **A Manager may approve invoices up to 50,000.00; this invoice is 500,000.00 and needs a Director.**",
                "The invoice is still waiting; the Approve button is still there."],
               "The limit is enforced by role, the user is told exactly why, and a refusal changes nothing. This is the screen the browser test checks.",
               "This is the key screen of the assignment: the refusal reason and the unchanged invoice.")

    shot_slide(deck, "The rules", "A Director sees the larger invoices", "07-director-pending-list.png", "Signed in as demo.director (Director)",
               ["The same list, signed in as a Director.",
                "INV-2001 (75,000.00) can be approved here; INV-2002 is still **0 of 2 approvals**.",
                "The header shows who is signed in and their role."],
               "Between 50,000.01 and 500,000.00 one Director is enough. Above 500,000.00 the first approval only moves the counter.")

    shot_slide(deck, "The rules", "The same Director cannot approve twice", "08-same-director-refused.png", "Signed in as demo.director (Director)",
               ["INV-2002 now shows **1 of 2 approvals**: this Director approved once.",
                "Approving again gives: **demo.director has already approved this invoice; invoices above 500,000.00 need two different approvers.**",
                "INV-2001, already approved, has left the list."],
               "The first negative rule: the same user never counts as both approvers, and the refused second attempt changes nothing.")

    shot_slide(deck, "The rules", "A second, different Director takes over", "09-second-director-pending-list.png", "Signed in as demo.director2 (Director)",
               ["After signing out and in as **demo.director2**, INV-2002 still reads **1 of 2 approvals**.",
                "The first approval was kept; it is waiting for a different Director.",
                "The message from the previous screen is gone: it is cleared on sign-out and sign-in."],
               "The invoice has been waiting in a valid state, not lost or half-written.")

    shot_slide(deck, "The rules", "Two approvals complete the invoice", "10-fully-approved.png", "Signed in as demo.director2 (Director)",
               ["On the Invoices tab INV-2002 is now **Approved**.",
                "Rejected invoices carry a red **Rejected** pill.",
                "Nothing is left in a half-approved state."],
               "Above 500,000.00 the invoice becomes Approved only when two different users, the second a Director, have approved.")

    shot_slide(deck, "The rules", "Admin has nothing to approve", "11-admin-nothing-pending.png", "Signed in as demo.admin (Admin)",
               ["The Approvals tab shows **Nothing is waiting for approval.** once every invoice has a decision.",
                "An empty list is a normal state with its own message."],
               "Every pending invoice went through the rules; the queue is empty and nothing is stuck.")

    shot_slide(deck, "The rules", "Admin may look, but not approve", "13-admin-cannot-approve.png", "Signed in as demo.admin (Admin)",
               ["INV-1007 (6,000,000.00) is waiting, **0 of 2 approvals**.",
                "Approve was pressed as Admin: **Role Admin is not allowed to approve invoices.**",
                "The invoice is unchanged."],
               "Admin can reject and delete but never approve. The role check comes first, before any amount rule.")

    shot_slide(deck, "Invoices", "Creating a draft invoice", "12-new-draft-invoice.png", "Signed in as demo.admin (Admin)",
               ["A new invoice **INV-1006** for 500,000.00 appears as **Draft**.",
                "It has a **Submit for approval** button; it is not in anyone's approval queue yet.",
                "Amounts are checked on the server: zero, negative, sub-cent and huge values are rejected."],
               "An invoice moves Draft, then Pending, then Approved or Rejected. Amounts are exact decimals, never floating point.")

    shot_slide(deck, "Invoices", "Rejection reasons stay visible", "14-rejection-reasons-shown.png", "Signed in as demo.director (Director)",
               ["Rejected invoices show the reason under the pill: **Reason: … (rejected by demo.manager)**.",
                "Anyone who opens the Invoices tab can see who rejected an invoice and why."],
               "A rejection is accountable: the decider and the reason are stored with the invoice and shown to everyone.")

    terminal_slide(deck, "Evidence", "Unit tests: 177 passed", "20-unit-tests-177-passed.png", "python -m pytest backend/tests -q",
                   [("What ran", "63 policy tests, 62 service tests, 36 API tests and 16 repository-contract tests."),
                    ("What they prove", "Every rule and boundary, the two negative rules, and that a refusal leaves the invoice unchanged."),
                    ("One warning", "A third-party deprecation notice about the test client; it does not affect the result.")])

    terminal_slide(deck, "Evidence", "The two negative rules, run on their own", "21-negative-rules-tests.png",
                   'python -m pytest backend/tests/test_approval_policy.py -v -k "same_user or second_approver"',
                   [("Same user twice", "Refused, including `Dir.One`, ` dir.one ` and tab or space padding."),
                    ("Manager as second approver", "Refused with a reason above 500,000.00."),
                    ("12 passed", "51 other tests were skipped by the filter; this view is only the two rules.")])

    terminal_slide(deck, "Evidence", "Mutation testing: 100%", "22-mutation-score-100.png", "wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh demo",
                   [("What it does", "Changes the domain code 132 different ways, one at a time, and runs the tests."),
                    ("The result", "132 killed, 0 survived: the tests noticed every change."),
                    ("Why it matters", "A high line-coverage number does not say whether tests can fail; this does.")])

    terminal_slide(deck, "Evidence", "Browser test: 1 passed", "23-playwright-one-passed.png", "cd e2e; npx playwright test --headed; cd ..",
                   [("What it does", "Drives the real UI as a Manager and tries to approve an over-limit invoice."),
                    ("What it checks", "The exact refusal reason, and that the invoice stays Pending Approval."),
                    ("Clean up", "The test creates its own invoice and removes it, so it can run again and again.")])

    slide = content_slide(deck, "Summary", "Every screen, and the rule it proves")
    table(slide, 0.6, 1.5, 12.13, [("Screen", 0.34), ("Rule or behaviour proven", 0.66)], [
        ["Sign-in and wrong password", "Everything is behind sign-in; failures are generic."],
        ["Reject with and without a reason", "A reason is required, stored and shown with who rejected."],
        ["Manager refused on 500,000.00", "Role limits are enforced with a clear reason; nothing changes."],
        ["Same Director refused on INV-2002", "The same user never counts twice above 500,000.00."],
        ["Second Director completes INV-2002", "Two different approvers, the second a Director, are required."],
        ["Admin refused", "Admin can reject and delete but never approve."],
        ["Draft and Submit", "Invoices move Draft, Pending, then Approved or Rejected."],
        ["Test, mutation and browser output", "177 tests, 100% mutation score and 1 browser test, all repeatable."],
    ], size=13, first_bold=True, pad=0.09)

    closing_slide(deck, "Try it yourself", [
        "Start the app: `python -m uvicorn invoice_app.api.main:app --app-dir backend/src --port 5000`",
        "Open `http://localhost:5000` and sign in as `demo.manager`",
        "Approve INV-2001 and read the refusal, then try again as `demo.director`",
        "Approve INV-2002 as `demo.director`, then as `demo.director2`",
    ], "Invite the viewer to follow the same path on their own machine.")
    return deck


def main() -> None:
    """Build both decks."""
    reviewer_deck().build("Invoice-Approval-Reviewer-Walkthrough")
    ui_deck().build("Invoice-Approval-UI-Walkthrough")


if __name__ == "__main__":
    main()
