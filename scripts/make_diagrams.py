"""Draw the architecture diagrams as SVG and render them to PNG.

    python scripts/make_diagrams.py

Output: docs/guides/img/diagrams/<name>.svg and <name>.png (2x). The guides and both slide decks use the PNGs.
Every box names a real file or class of this repository; if the code changes, change the matching box here.
Needs: pip install playwright && playwright install chromium
"""

import html
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "guides" / "img" / "diagrams"

# Palette shared with the PDF guides and the slide decks.
NAVY, NAVY2, TEAL, TEAL_D, TEAL_SOFT = "#0b1e3f", "#13315f", "#14b8a6", "#0b7f7a", "#e6f6f4"
INK, MUTED, LINE, PAPER, WHITE = "#1b2638", "#5d6b7c", "#d3dce6", "#f4f7fb", "#ffffff"
RED, RED_SOFT, AMBER, AMBER_SOFT, GREEN, GREEN_SOFT = "#b4452f", "#fdebe7", "#9a6a00", "#fff4d6", "#0b7f7a", "#e3f4f1"
FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"


def esc(text: str) -> str:
    """Escape text for SVG."""
    return html.escape(text, quote=False)


class Svg:
    """A tiny SVG builder: boxes, text, arrows. Coordinates are pixels on a fixed canvas."""

    def __init__(self, width: int, height: int) -> None:
        """Start an empty canvas of the given size."""
        self.width, self.height, self.parts = width, height, []

    def add(self, raw: str) -> None:
        """Append raw SVG."""
        self.parts.append(raw)

    def rect(self, x, y, w, h, fill=WHITE, stroke=LINE, r=12, sw=1.5, dash=None, shadow=False) -> None:
        """A rounded rectangle."""
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        filt = ' filter="url(#shadow)"' if shadow else ""
        stroke_attr = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"{stroke_attr}{dash_attr}{filt}/>')

    def text(self, x, y, content: str, size=15, weight=400, fill=INK, anchor="start", mono=False, leading=1.32) -> None:
        """Text; ``\\n`` starts a new line. y is the baseline of the first line."""
        family = MONO if mono else FONT
        lines = content.split("\n")
        spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else round(size * leading, 1)}">{esc(line) or chr(160)}</tspan>' for i, line in enumerate(lines))
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{spans}</text>')

    def card(self, x, y, w, h, title: str, body: str = "", fill=WHITE, stroke=LINE, title_fill=NAVY, size=14, mono_title=False, body_fill=INK) -> None:
        """A white card with a bold title and a few body lines."""
        self.rect(x, y, w, h, fill=fill, stroke=stroke, shadow=True)
        lines = title.count("\n") + 1
        self.text(x + 14, y + 25, title, size=size + 1, weight=700, fill=title_fill, mono=mono_title)
        if body:
            self.text(x + 14, y + 25 + lines * round((size + 1) * 1.32) + 4, body, size=size, fill=body_fill)

    def container(self, x, y, w, h, label: str, fill=PAPER, stroke="#b9c6d5", label_fill=MUTED, dash=None) -> None:
        """A large background group with a small caps label."""
        self.rect(x, y, w, h, fill=fill, stroke=stroke, r=18, sw=1.6, dash=dash)
        self.text(x + 18, y + 24, label.upper(), size=12, weight=700, fill=label_fill)

    def pill(self, x, y, w, h, content: str, fill=NAVY, color=WHITE, size=14, weight=600) -> None:
        """A fully rounded label."""
        self.rect(x, y, w, h, fill=fill, stroke=None, r=h / 2)
        self.text(x + w / 2, y + h / 2 + size * 0.35, content, size=size, weight=weight, fill=color, anchor="middle")

    def diamond(self, cx, cy, w, h, content: str, fill=AMBER_SOFT, stroke=AMBER, size=14) -> None:
        """A decision diamond with centred text."""
        points = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
        self.add(f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        lines = content.count("\n") + 1
        self.text(cx, cy - (lines - 1) * size * 0.66 + size * 0.35, content, size=size, weight=600, fill=INK, anchor="middle")

    def arrow(self, points, color=NAVY, dash=None, sw=2.2, label="", label_at=None, label_size=12, label_fill=None, head=True) -> None:
        """A polyline with an arrow head at the end and an optional label."""
        marker = {NAVY: "navy", TEAL_D: "teal", RED: "red", MUTED: "grey", GREEN: "teal", AMBER: "amber"}.get(color, "navy")
        path = " ".join(f"{px},{py}" for px, py in points)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        end = f' marker-end="url(#head-{marker})"' if head else ""
        self.add(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round"{dash_attr}{end}/>')
        if label:
            lx, ly = label_at if label_at else ((points[0][0] + points[-1][0]) / 2, (points[0][1] + points[-1][1]) / 2 - 8)
            self.text(lx, ly, label, size=label_size, weight=600, fill=label_fill or color, anchor="middle")

    def svg(self) -> str:
        """The finished SVG document."""
        heads = "".join(
            f'<marker id="head-{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for name, color in (("navy", NAVY), ("teal", TEAL_D), ("red", RED), ("grey", MUTED), ("amber", AMBER))
        )
        defs = (f'<defs>{heads}<filter id="shadow" x="-5%" y="-5%" width="110%" height="120%">'
                '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0b1e3f" flood-opacity="0.10"/></filter></defs>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">'
                f'<rect width="{self.width}" height="{self.height}" fill="{WHITE}"/>{defs}{"".join(self.parts)}</svg>')


def architecture() -> Svg:
    """Layers drawn as stacked rows: people and browser, the web layer, the domain, and the concrete parts."""
    d = Svg(1600, 860)
    # Row 1: people, browser, end-to-end test
    for i, role in enumerate(("Manager", "Director", "Admin")):
        d.pill(30, 22 + i * 46, 130, 38, role, fill=TEAL_D, size=16)
    d.arrow([(166, 80), (210, 80)], color=MUTED)
    d.card(220, 20, 820, 136, "Browser: static web UI (wwwroot)",
           "index.html: sign-in, Invoices tab, Approvals tab.   styles.css: design tokens, status pills.\napp.js: plain JavaScript, no build step. Sends the session token as Authorization: Bearer\nand shows the refusal reason, the rejection reason and \"N of M approvals\".", size=15)
    d.card(1090, 20, 480, 136, "Playwright end-to-end test", "Page objects, role-based locators.\nDrives this same UI on port 5000 and\nchecks the exact refusal text.", size=15)
    d.arrow([(1090, 88), (1042, 88)], color=MUTED, label="drives", label_at=(1066, 76), label_size=13)
    d.arrow([(630, 156), (630, 206)], label="HTTP + JSON, Bearer token", label_at=(760, 188), label_size=14)
    # Row 2: web layer
    d.container(30, 206, 1540, 244, "api/  the web layer (FastAPI)")
    web = [("main.py", "create_app(repository,\nusers, policy):\nthe composition root; the\nonly place that picks\nconcrete classes"),
           ("auth/middleware.py", "Session check: no valid\ntoken means 401, before\nany router runs"),
           ("routers/", "auth: login, logout\ninvoices: list, get, create,\nsubmit, delete (Admin)\napprovals: approve, reject"),
           ("error_handling.py", "Domain error to HTTP:\nnot found 404, wrong state\n409, not permitted 403,\nbad input 400, other 500"),
           ("serialization.py\nstatic_ui.py", "Invoice to camelCase JSON;\nUI served with no-cache")]
    for i, (title, body) in enumerate(web):
        x = 50 + i * 303
        d.card(x, 244, 290, 190, title, body, size=14)
    d.arrow([(630, 450), (630, 494)], label="routers call the domain; no rules in the web layer", label_at=(960, 478), label_size=14)
    # Row 3: domain
    d.container(30, 494, 1540, 244, "domain/  business rules: no web code, no storage code", fill="#eefaf8", stroke="#9ed8d1", label_fill=TEAL_D)
    dom = [("approval_service.py", "ApprovalService:\nsubmit, approve, reject.\nOne lock; every check runs\nbefore the first change"),
           ("approval_policy.py", "ApprovalPolicy asks the rules\nin order; first objection wins:\n1 ApproverRoleRule\n2 ManagerLimitRule\n3 DistinctApproversRule\n4 SecondApproverMustBeDirector"),
           ("repository.py", "Contracts (Protocols):\nApprovalStore, InvoiceReader,\nInvoiceWriter,\nInvoiceRepository"),
           ("invoice.py, approval.py\nerrors.py", "Invoice (with ordered\napprovals), Approver,\nApprovalRecord, status;\nfour domain errors. Money\nis Decimal, never float")]
    widths = [320, 430, 320, 330]
    x = 50
    for (title, body), width in zip(dom, widths):
        d.card(x, 532, width, 192, title, body, size=14)
        x += width + 20
    # Row 4: concrete parts
    d.rect(30, 770, 1540, 76, fill="#eef3f9", stroke="#aebbcc", r=14, dash="7 5")
    d.text(48, 800, "CONCRETE PARTS THE DEMO USES\n(chosen in create_app)", size=12.5, weight=700, fill=MUTED)
    for i, (name, body) in enumerate((("in_memory_repository", "thread-safe, seeded invoices"), ("session_store", "tokens in memory"), ("user_directory", "four demo accounts"))):
        d.rect(330 + i * 410, 782, 392, 52, fill=WHITE, stroke=LINE, r=10)
        d.text(344 + i * 410, 805, name, size=15, weight=700, fill=NAVY, mono=True)
        d.text(344 + i * 410, 825, body, size=13.5, fill=MUTED)
    d.arrow([(960, 770), (960, 726)], color=TEAL_D, dash="7 5", label="implement the contracts", label_at=(1112, 752), label_size=14)
    return d


def _lifelines(d: Svg, bottom: int) -> None:
    """The six boxes and dashed lifelines of the sequence diagram."""
    for name, x in (("Browser\napp.js", 120), ("Session\nmiddleware", 370), ("Approvals\nrouter", 620), ("ApprovalService", 880), ("ApprovalPolicy", 1130), ("Repository", 1400)):
        d.rect(x - 95, 16, 190, 66, fill=NAVY, stroke=None, r=10)
        d.text(x, 46 if "\n" in name else 56, name, size=17, weight=700, fill=WHITE, anchor="middle")
        d.add(f'<line x1="{x}" y1="82" x2="{x}" y2="{bottom}" stroke="#b9c6d5" stroke-width="1.8" stroke-dasharray="6 6"/>')


def _message(d: Svg, y, x1, x2, label, color=NAVY, dash=None) -> None:
    """A horizontal message arrow with a label above it."""
    d.arrow([(x1, y), (x2, y)], color=color, dash=dash, label=label, label_at=((x1 + x2) / 2, y - 10), label_size=15)


def _note(d: Svg, y, cx, content, width=270, height=46, fill=AMBER_SOFT, stroke=AMBER) -> None:
    """A note box over a lifeline."""
    d.rect(cx - width / 2, y, width, height, fill=fill, stroke=stroke, r=8, sw=1.3)
    lines = content.count("\n") + 1
    d.text(cx, y + height / 2 - (lines - 1) * 8 + 5, content, size=14, weight=600, anchor="middle")


def sequence_steps() -> Svg:
    """Steps 1 to 6 of an approve request: sign-in check, role check, lock, load, policy."""
    d = Svg(1600, 760)
    _lifelines(d, 744)
    for number, y in ((1, 128), (2, 214), (3, 300), (4, 400), (5, 490), (6, 620)):
        d.text(30, y, str(number), size=20, weight=800, fill=TEAL_D)
    _message(d, 128, 120, 370, "POST /api/approvals/INV-2001/approve")
    d.text(130, 154, "Authorization: Bearer <token>", size=13.5, fill=MUTED)
    _note(d, 176, 370, "No valid token?  401, stop", width=270)
    _message(d, 262, 370, 620, "session attached")
    _note(d, 282, 620, "require_role(Manager,\nDirector, Admin)?\nElse 403", width=250, height=66)
    _message(d, 400, 620, 880, "approve(id, Approver(username, role))")
    _note(d, 420, 880, "take the lock", width=250, height=40, fill=TEAL_SOFT, stroke=TEAL_D)
    _message(d, 506, 880, 1400, "get_by_id(id)")
    _message(d, 548, 1400, 880, "the invoice", dash="6 5")
    _note(d, 566, 880, "unknown id? 404\nnot PendingApproval? 409", width=290, height=56)
    _message(d, 664, 880, 1130, "refusal_reason(amount, approver, approvals)")
    _note(d, 684, 1130, "rules in order: role, manager limit,\nsame user, second is a Director", width=330, height=56)
    return d


def sequence_outcomes() -> Svg:
    """Step 7: the policy answers, then either the refused path or the allowed path."""
    d = Svg(1600, 700)
    _lifelines(d, 684)
    d.text(30, 128, "7", size=20, weight=800, fill=TEAL_D)
    _message(d, 128, 1130, 880, "None, or the reason text", dash="6 5")
    d.rect(60, 160, 1480, 236, fill=RED_SOFT, stroke=RED, r=12, sw=1.6, dash="8 5")
    d.text(80, 190, "REFUSED  (a reason came back)", size=15, weight=800, fill=RED)
    _message(d, 262, 880, 620, "raise ApprovalNotPermittedError(reason)", color=RED)
    _message(d, 332, 620, 120, "403  {\"error\": \"<reason>\"}", color=RED)
    d.text(930, 236, "Nothing has been changed: no record added,\nno status change, no save.", size=15, weight=700, fill=RED)
    d.text(930, 362, "The UI shows the reason; the invoice looks exactly as before.", size=14.5)
    d.rect(60, 416, 1480, 262, fill=GREEN_SOFT, stroke=GREEN, r=12, sw=1.6, dash="8 5")
    d.text(80, 446, "ALLOWED  (no reason)", size=15, weight=800, fill=GREEN)
    d.text(80, 482, "add an ApprovalRecord. When approvals reach the\nrequired count (1, or 2 above 500,000.00):\nstatus Approved, decided_by and decided_at set.", size=14.5, weight=600)
    _message(d, 528, 880, 1400, "update(invoice)", color=GREEN)
    _message(d, 590, 880, 620, "the invoice", color=GREEN, dash="6 5")
    _message(d, 650, 620, 120, "200  invoice JSON (requiredApprovals, approvals)", color=GREEN)
    return d


def approval_gates() -> Svg:
    """The first three questions: state, role, amount band."""
    d = Svg(1600, 470)
    d.rect(20, 130, 250, 100, fill=NAVY, stroke=None, r=16)
    d.text(145, 168, "Someone presses\nApprove on an invoice\nof amount A", size=16, weight=700, fill=WHITE, anchor="middle")
    d.arrow([(270, 180), (350, 180)])
    d.diamond(520, 180, 340, 160, "Is the invoice\nPendingApproval?", size=17)
    d.arrow([(690, 180), (730, 180)], label="yes", label_at=(710, 168), label_size=14)
    d.diamond(900, 180, 340, 160, "Is the approver a\nManager or Director?", size=17)
    d.arrow([(1070, 180), (1150, 180)], label="yes", label_at=(1110, 168), label_size=14)
    d.diamond(1360, 180, 400, 160, "Is the amount A\nabove 500,000.00 ?", size=17)
    for cx, text_, reason in ((520, "409  Only pending invoices\ncan be decided.", "(404 first for an unknown id)"), (900, "403  Role Admin is not\nallowed to approve invoices.", "")):
        d.arrow([(cx, 260), (cx, 316)], color=RED, label="no", label_at=(cx + 22, 292), label_size=14)
        d.rect(cx - 160, 316, 320, 92 if not reason else 92, fill=RED_SOFT, stroke=RED, r=10)
        d.text(cx - 144, 346, text_, size=15, weight=700, fill=RED)
        if reason:
            d.text(cx - 144, 392, reason, size=13, fill=MUTED)
    d.arrow([(1260, 220), (1260, 316)], label="yes", label_at=(1286, 284), label_size=14)
    d.arrow([(1470, 220), (1470, 316)], label="no", label_at=(1494, 284), label_size=14)
    d.pill(1130, 316, 260, 44, "two approvers needed", fill=NAVY2, size=15)
    d.pill(1400, 316, 180, 44, "one approver", fill=NAVY2, size=15)
    d.text(1260, 392, "see the next diagram", size=13.5, fill=MUTED, anchor="middle")
    d.text(1490, 392, "see the next diagram", size=13.5, fill=MUTED, anchor="middle")
    d.rect(20, 428, 1560, 34, fill=TEAL_SOFT, stroke="#9ed8d1", r=10)
    d.text(36, 451, "Every refusal is decided before anything is changed: the invoice stays exactly as it was.", size=15, weight=700, fill=TEAL_D)
    return d


def approval_branches() -> Svg:
    """The rules for the two amount bands."""
    d = Svg(1600, 860)
    d.container(20, 16, 1560, 408, "Above 500,000.00: two different approvers", fill="#eef3f9")
    d.diamond(330, 190, 420, 170, "Has this same user\nalready approved it?\n(trim spaces, ignore case)", size=16)
    d.arrow([(330, 275), (330, 316)], color=RED, label="yes", label_at=(356, 302), label_size=14)
    d.rect(100, 316, 460, 98, fill=RED_SOFT, stroke=RED, r=10)
    d.text(116, 342, "403  Dir.One has already approved this\ninvoice; invoices above 500,000.00 need\ntwo different approvers.", size=14, weight=700, fill=RED)
    d.arrow([(540, 190), (640, 190)], label="no", label_at=(590, 178), label_size=14)
    d.diamond(850, 190, 440, 170, "Is it the second approval and\nthe approver is not\na Director?", size=16)
    d.arrow([(850, 275), (850, 316)], color=RED, label="yes", label_at=(876, 302), label_size=14)
    d.rect(620, 316, 460, 98, fill=RED_SOFT, stroke=RED, r=10)
    d.text(636, 342, "403  The second approver on an invoice\nabove 500,000.00 must be a Director;\ndemo.manager is a Manager.", size=14, weight=700, fill=RED)
    d.arrow([(1070, 190), (1170, 190)], label="no", label_at=(1120, 178), label_size=14)
    d.rect(1170, 120, 390, 150, fill=GREEN_SOFT, stroke=GREEN, r=12)
    d.text(1190, 152, "Record the approval", size=17, weight=800, fill=GREEN)
    d.text(1190, 182, "First of two: the invoice stays\nPending (\"1 of 2 approvals\").\nSecond: status Approved.", size=14.5, weight=600)
    d.container(20, 444, 1560, 330, "Up to 500,000.00: one approver is enough", fill="#eef3f9")
    d.diamond(400, 610, 500, 170, "Is A above 50,000.00 and the\napprover is not a Director?", size=16)
    d.arrow([(650, 610), (760, 610)], label="yes", label_at=(705, 598), label_size=14)
    d.rect(760, 548, 450, 124, fill=RED_SOFT, stroke=RED, r=10)
    d.text(776, 578, "403  A Manager may approve invoices up to\n50,000.00; this invoice is 75,000.00 and\nneeds a Director.", size=14, weight=700, fill=RED)
    d.arrow([(400, 695), (400, 728), (1300, 728), (1300, 690)], label="no", label_at=(850, 718), label_size=14)
    d.rect(1230, 520, 330, 170, fill=GREEN_SOFT, stroke=GREEN, r=12)
    d.text(1250, 552, "Record the approval", size=17, weight=800, fill=GREEN)
    d.text(1250, 582, "One approval is enough:\nstatus Approved (\"1 of 1\").", size=14.5, weight=600)
    d.text(20, 812, "Rule order: role, Manager limit, \"same user\", \"second must be a Director\". The first objection wins and its text is the reason shown.", size=14.5, fill=MUTED)
    d.text(20, 838, "Limits are inclusive: 50,000.00 and 500,000.00 are inside their band; one cent more moves to the next band.", size=14.5, fill=MUTED)
    return d


def bands() -> Svg:
    """The approval bands and who may approve in each."""
    d = Svg(1600, 640)
    segs = [(40, 470, "Up to 50,000.00", "1 approval", "Manager or Director", TEAL_SOFT, TEAL_D),
            (510, 470, "50,000.01 to 500,000.00", "1 approval", "Director only", AMBER_SOFT, AMBER),
            (980, 580, "Above 500,000.00", "2 approvals, 2 different users", "First: Manager or Director\nSecond: a Director", "#e8eefb", NAVY2)]
    for x, w, title, count, who, fill, color in segs:
        d.rect(x, 90, w, 140, fill=fill, stroke=color, r=14, sw=2)
        d.text(x + w / 2, 134, title, size=22, weight=800, fill=color, anchor="middle")
        d.text(x + w / 2, 166, count, size=16, weight=700, fill=INK, anchor="middle")
        d.text(x + w / 2, 192, who.split("\n")[0], size=14, fill=INK, anchor="middle")
        if "\n" in who:
            d.text(x + w / 2, 212, who.split("\n")[1], size=14, fill=INK, anchor="middle")
    for x, lo, hi in ((510, "50,000.00", "50,000.01"), (980, "500,000.00", "500,000.01")):
        d.add(f'<line x1="{x}" y1="60" x2="{x}" y2="244" stroke="{NAVY}" stroke-width="2.4" stroke-dasharray="5 4"/>')
        d.text(x - 12, 52, lo + "  in the lower band", size=13, weight=700, fill=NAVY, anchor="end")
        d.text(x + 12, 52, hi + "  in the next band", size=13, weight=700, fill=RED, anchor="start")
    d.text(800, 276, "Limits are inclusive. The tests try one cent either side of both limits.", size=14.5, weight=600, fill=MUTED, anchor="middle")
    # Role matrix
    heads = ["", "Up to 50,000.00", "50,000.01 to 500,000.00", "Above 500,000.00"]
    rows = [("Manager", ["approves", "refused: needs a Director", "may be the FIRST approver only"], [GREEN, RED, AMBER]),
            ("Director", ["approves", "approves", "first or second approver"], [GREEN, GREEN, GREEN]),
            ("Admin", ["never approves", "never approves", "never approves"], [RED, RED, RED])]
    x0, y0, cw, rh = 40, 310, [220, 400, 460, 460], 62
    xs = [x0]
    for width in cw[:-1]:
        xs.append(xs[-1] + width)
    d.rect(x0, y0, sum(cw), rh, fill=NAVY, stroke=None, r=12)
    for i, head in enumerate(heads):
        d.text(xs[i] + 18, y0 + 38, head, size=15, weight=700, fill=WHITE)
    for r, (name, cells, colors) in enumerate(rows):
        y = y0 + rh * (r + 1) + 6
        d.rect(x0, y, sum(cw), rh - 6, fill=WHITE if r % 2 == 0 else PAPER, stroke=LINE, r=10)
        d.text(xs[0] + 18, y + 36, name, size=16, weight=800, fill=NAVY)
        for i, (cell, color) in enumerate(zip(cells, colors), start=1):
            d.text(xs[i] + 18, y + 36, cell, size=15, weight=700, fill=color)
    d.text(40, y0 + rh * 4 + 40, "Above 500,000.00 the same user can never count twice (names compared after trim and ignoring case), and a refused attempt changes nothing.", size=14, fill=MUTED)
    return d


def lifecycle() -> Svg:
    """The invoice states and what moves it."""
    d = Svg(1600, 560)
    nodes = {"Draft": (60, 200, "#eef1f5", MUTED), "PendingApproval": (500, 200, AMBER_SOFT, AMBER),
             "Approved": (1080, 70, GREEN_SOFT, GREEN), "Rejected": (1080, 330, RED_SOFT, RED)}
    for name, (x, y, fill, color) in nodes.items():
        d.rect(x, y, 300 if name != "PendingApproval" else 340, 110, fill=fill, stroke=color, r=18, sw=2.4, shadow=True)
        d.text(x + (150 if name != "PendingApproval" else 170), y + 66, name, size=24, weight=800, fill=color, anchor="middle")
    d.pill(60, 100, 150, 36, "Create invoice", fill=NAVY, size=14)
    d.arrow([(135, 136), (135, 198)])
    d.arrow([(360, 255), (498, 255)], label="submit", label_at=(430, 244), label_size=14)
    d.arrow([(840, 232), (960, 232), (960, 125), (1078, 125)], color=GREEN, label="approve: required count reached", label_at=(960, 112), label_size=13)
    d.arrow([(840, 278), (960, 278), (960, 385), (1078, 385)], color=RED, label="reject with a reason", label_at=(1019, 372), label_size=13)
    # Self-loop on pending
    d.add(f'<path d="M 560 198 C 540 120, 800 120, 780 198" fill="none" stroke="{AMBER}" stroke-width="2.4" marker-end="url(#head-amber)"/>')
    d.text(670, 118, "approve, but more are needed (\"1 of 2 approvals\")", size=13, weight=700, fill=AMBER, anchor="middle")
    d.rect(60, 460, 1480, 76, fill=TEAL_SOFT, stroke="#9ed8d1", r=12)
    d.text(80, 490, "A refused approval (403) is not a transition: the invoice stays in the same state with the same approvals.", size=14.5, weight=700, fill=TEAL_D)
    d.text(80, 516, "Wrong state (for example approving an already Approved invoice) is a 409; an unknown id is a 404. Admin can also delete an invoice.", size=13.5, fill=INK)
    d.text(1230, 222, "decided_by and decided_at are set only by the\nfinal approval or by a rejection", size=12.5, fill=MUTED, anchor="middle")
    return d


def ai_pipeline() -> Svg:
    """The seven steps from context file to reviewed pull request, and what each produces."""
    d = Svg(1600, 400)
    steps = [("1  Context", "AGENTS.md\nCLAUDE.md imports it\nskills: approval-rules,\nreview-findings,\nrun-checks"),
             ("2  Spec", "Spec Kit:\nconstitution, specify,\nclarify, plan, tasks\n(spec-writer agent)"),
             ("3  Build", "implementer agent:\none task group at a\ntime, tests first,\nthen code"),
             ("4  Review tests", "test-reviewer agent:\nKEEP / STRENGTHEN /\nREMOVE each test"),
             ("5  Mutation", "mutmut on domain/;\nmutation-analyst agent\nclassifies survivors"),
             ("6  Browser test", "Playwright: a manager\nis refused on a\n75,000.00 invoice"),
             ("7  PR review", "pr-reviewer agent:\n11 findings, each\nfixed, dismissed or\ndeferred")]
    w, gap, x0 = 200, 22, 30
    for i, (title, body) in enumerate(steps):
        x = x0 + i * (w + gap)
        d.rect(x, 20, w, 258, fill=WHITE, stroke=LINE, r=14, shadow=True)
        d.rect(x, 20, w, 56, fill=NAVY, stroke=None, r=14)
        d.rect(x, 56, w, 20, fill=NAVY, stroke=None, r=0)
        d.text(x + 16, 56, title, size=18, weight=800, fill=WHITE)
        d.text(x + 16, 112, body, size=15, fill=INK)
        if i < len(steps) - 1:
            d.arrow([(x + w + 2, 150), (x + w + gap - 2, 150)], color=TEAL_D)
    d.text(30, 308, "OUTPUT OF EACH STEP", size=12.5, weight=700, fill=MUTED)
    outs = ["rules every agent follows", "specs/001-invoice-\napproval-limits/", "backend/src, backend/tests", "stronger tests, 2 removed", "63.9% to 100% (132/132)", "over-limit-rejection.spec", "docs/pr-review.md"]
    for i, content in enumerate(outs):
        d.rect(x0 + i * (w + gap), 320, w, 60, fill=TEAL_SOFT, stroke=None, r=14)
        d.text(x0 + i * (w + gap) + w / 2, 346 if "\n" not in content else 340, content, size=14, weight=700, fill=TEAL_D, anchor="middle")
    return d


def ai_automation() -> Svg:
    """Hooks that log every event, and the five agents."""
    d = Svg(1600, 600)
    d.container(30, 10, 1540, 330, "Hooks: run automatically on every Claude Code event (.claude/settings.json)", fill="#eef3f9")
    hooks = [("log_event.py", "Prompt, tool use, sub-agent\nstop, session stop:\none JSON line, 27 fixed\nkeys per event"),
             ("check_summary.py", "After shell commands:\npytest, mutmut, Playwright\nbecome CHECK name | metrics\n| result=pass/fail"),
             ("validate_review.py", "When a sub-agent stops:\nblocks a pr-reviewer answer\nthat is not the findings\nJSON schema")]
    for i, (name, body) in enumerate(hooks):
        d.card(50 + i * 318, 46, 300, 190, name, body, size=15, mono_title=True)
    d.arrow([(984, 140), (1010, 140)], color=TEAL_D)
    d.card(1014, 46, 270, 190, "logs/ai-interactions.jsonl", "Append-only: prompt, tools,\nsub-agents, AI suggestion,\nhuman decision, verification,\nstatus, files", size=14, mono_title=True)
    d.arrow([(1286, 140), (1310, 140)], color=TEAL_D)
    d.card(1314, 46, 240, 190, "summarize_log.py", "Validates every line and\nwrites the readable\nsummary, counting prompts\nand human decisions", size=14, mono_title=True)
    d.text(50, 268, "Secrets, local paths and the account name are removed before a line is written. A hook never fails a session.", size=15, fill=MUTED)
    d.text(50, 300, "Human corrections are recorded too:  python .claude/hooks/log_event.py --human \"what I decided\"", size=14.5, fill=MUTED, mono=True)
    d.container(30, 360, 1540, 230, "Agents (.claude/agents)  and skills (.claude/skills)")
    agents = [("spec-writer", "read, write\nwrites Spec Kit files only"), ("implementer", "read, write, shell\none task group at a time"),
              ("test-reviewer", "read-only\nfinds tests that cannot fail"), ("pr-reviewer", "read-only\nanswers in findings JSON only"), ("mutation-analyst", "read-only\nsurvivors to missing tests")]
    for i, (name, body) in enumerate(agents):
        d.card(50 + i * 302, 400, 286, 168, name, body, size=15, mono_title=True)
    return d


def pyramid() -> Svg:
    """The test layers and what each one proves."""
    d = Svg(1600, 740)
    layers = [("Browser test (Playwright)", "1 test", "Manager is refused on a 75,000.00 invoice;\nthe exact reason is shown; the invoice stays pending", 520, NAVY2),
              ("API tests", "36 tests", "Status codes, JSON shape, sign-in, roles, amount validation, double-click", 760, TEAL_D),
              ("Service tests + repository contract", "62 + 16 tests", "Lifecycle, \"unchanged after a refusal\", saved once, concurrency, fake equals real", 1000, "#0f8f84"),
              ("Policy tests", "63 tests", "Every rule, one cent either side of 50,000.00 and 500,000.00, the two negative rules", 1240, "#1aa89b")]
    cx, y = 680, 40
    for title, count, body, width, color in layers:
        d.rect(cx - width / 2, y, width, 118, fill=color, stroke=None, r=14)
        d.text(cx, y + 40, title, size=19, weight=800, fill=WHITE, anchor="middle")
        d.text(cx, y + 66, count, size=16, weight=700, fill="#d7f5f0", anchor="middle")
        d.text(cx, y + 92, body, size=12.5, fill=WHITE, anchor="middle")
        y += 132
    d.card(1330, 40, 240, 215, "Mutation testing", "mutmut changes the code\non purpose and checks a\ntest fails.\n\nBefore: 63.9%  (23/36)\nAfter:  100%  (132/132)", size=13.5, fill=TEAL_SOFT, stroke="#9ed8d1")
    d.card(1330, 275, 240, 190, "Hook tests", "10 tests in\n.claude/hooks that prove\nthe logger redacts secrets,\nkeeps 27 keys and survives\nbad input.", size=13.5)
    d.card(1330, 485, 240, 130, "Total", "177 backend tests\n10 hook tests\n1 browser test", size=14, fill=NAVY, stroke=NAVY, title_fill="#4be3d2", body_fill=WHITE)
    d.text(40, 590, "Each refusal test asserts the reason text, deep-compares the invoice before and after,", size=13.5, fill=MUTED)
    d.text(40, 612, "and checks the repository saw no update. A test that only checks the exception type does not count.", size=13.5, fill=MUTED)
    return d


DIAGRAMS = {
    "01-architecture-overview": architecture,
    "02a-approve-sequence-steps": sequence_steps,
    "02b-approve-sequence-outcomes": sequence_outcomes,
    "03a-approval-gates": approval_gates,
    "03b-approval-branches": approval_branches,
    "04-approval-bands": bands,
    "05-invoice-lifecycle": lifecycle,
    "06a-ai-pipeline": ai_pipeline,
    "06b-ai-automation": ai_automation,
    "07-test-layers": pyramid,
}


def main() -> None:
    """Write every diagram as SVG and PNG."""
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for name, build in DIAGRAMS.items():
            diagram = build()
            markup = diagram.svg()
            (OUT / f"{name}.svg").write_text(markup, encoding="utf-8")
            page = browser.new_page(viewport={"width": diagram.width, "height": diagram.height}, device_scale_factor=2)
            page.set_content(f"<html><body style='margin:0'>{markup}</body></html>")
            page.screenshot(path=str(OUT / f"{name}.png"), clip={"x": 0, "y": 0, "width": diagram.width, "height": diagram.height})
            page.close()
        browser.close()
    print(f"wrote {len(DIAGRAMS)} diagrams to {OUT}")


if __name__ == "__main__":
    main()
