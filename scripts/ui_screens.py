"""Turn the raw screenshots in UI/ into clean pictures for the guides and slides.

    python scripts/ui_screens.py

The raw files are full-screen captures (1920 x 1200): a browser tab strip and address bar on top, the Windows taskbar
below. This script never touches the originals. It writes cropped copies to docs/guides/img/ui/:

* browser shots: the tab strip, address bar, taskbar and scroll bar are removed, then the picture is cut tight around the
  white application card (``card``) or kept as the whole page without the browser frame (``page``);
* terminal shots: only the result lines are kept. The prompt lines (they show the folder path) are left out on purpose,
  so the pictures show what the command printed and nothing about the machine it ran on.
"""

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "UI"
TARGET = ROOT / "docs" / "guides" / "img" / "ui"

# Browser window geometry in the 1920 x 1200 captures: page area is below the address bar and above the taskbar,
# and the right-hand scroll bar sits in the last 18 pixels.
PAGE_LEFT, PAGE_TOP, PAGE_RIGHT, PAGE_BOTTOM = 6, 101, 1902, 1134
CARD_PADDING = 18
HEADER_GAP = 10  # space kept between the bottom of the navy header and the cut
WHITE = 255

# (screenshot number, output name, mode). Modes: "card" (cut around the white card), "page" (whole page, no browser
# frame), or ("rows", top, bottom, bottom_extra) for a terminal shot, see TERMINAL below.
BROWSER_SHOTS = [
    ("1799", "01-sign-in", "page"),
    ("1819", "02-invalid-sign-in", "card"),
    ("1802", "03-invoices-seed-data", "card"),
    ("1803", "04-reject-reason-typed", "card"),
    ("1811", "05-reason-required", "card"),
    ("1820", "06-manager-refused-over-limit", "card"),
    ("1806", "07-director-pending-list", "card"),
    ("1807", "08-same-director-refused", "card"),
    ("1809", "09-second-director-pending-list", "card"),
    ("1812", "10-fully-approved", "card"),
    ("1814", "11-admin-nothing-pending", "card"),
    ("1818", "12-new-draft-invoice", "card"),
    ("1823", "13-admin-cannot-approve", "card"),
    ("1826", "14-rejection-reasons-shown", "card"),
    ("1827", "15-rejection-reason-director", "card"),
    ("1801", "16-signed-in-page", "page"),
]

# Terminal shots: (screenshot number, output name, right edge in pixels, [(top, bottom), ...]).
# Several row ranges are joined with a thin gap; the right edge trims empty space so the text is larger on a slide.
TERMINAL_SHOTS = [
    ("1828", "20-unit-tests-177-passed", 640, [(1086, 1108)]),
    ("1829", "21-negative-rules-tests", 1902, [(232, 603)]),
    ("1830", "22-mutation-score-100", 1340, [(96, 368)]),
    ("1831", "23-playwright-one-passed", 1902, [(92, 314)]),
]


def white_card_box(pixels: np.ndarray) -> tuple[int, int, int, int]:
    """Bounding box (left, top, right, bottom) of the pure-white application card inside the page area."""
    is_white = (pixels[:, :, 0] == WHITE) & (pixels[:, :, 1] == WHITE) & (pixels[:, :, 2] == WHITE)
    columns = np.where(is_white.sum(axis=0) > 40)[0]
    rows = np.where(is_white.sum(axis=1) > 40)[0]
    return int(columns.min()), int(rows.min()), int(columns.max()), int(rows.max())


def header_bottom(pixels: np.ndarray) -> int:
    """First row below the dark navy header band at the top of the page (0 when the page is scrolled past it)."""
    column = pixels[:, pixels.shape[1] // 2, :]
    row = 0
    while row < len(column) and int(column[row].max()) < 100:
        row += 1
    return row


def browser_picture(path: Path, mode: str) -> Image.Image:
    """The page area of a browser capture, either whole or cut around the white card (never into the header)."""
    page = Image.open(path).convert("RGB").crop((PAGE_LEFT, PAGE_TOP, PAGE_RIGHT, PAGE_BOTTOM))
    if mode == "page":
        return page
    pixels = np.asarray(page)
    left, top, right, bottom = white_card_box(pixels)
    floor = header_bottom(pixels) + HEADER_GAP if header_bottom(pixels) else 0
    box = (max(left - CARD_PADDING, 0), max(top - CARD_PADDING, floor), min(right + CARD_PADDING, page.width), min(bottom + CARD_PADDING, page.height))
    return page.crop(box)


def terminal_picture(path: Path, right_edge: int, ranges: list[tuple[int, int]]) -> Image.Image:
    """The chosen row ranges of a terminal capture, stacked with a small gap, with a little margin on every side."""
    capture = Image.open(path).convert("RGB")
    background = capture.getpixel((1000, 700))
    strips = [capture.crop((0, top, right_edge, bottom)) for top, bottom in ranges]
    gap = 14 if len(strips) > 1 else 0
    height = sum(strip.height for strip in strips) + gap * (len(strips) - 1) + 24
    sheet = Image.new("RGB", (right_edge, height), background)
    y = 12
    for strip in strips:
        sheet.paste(strip, (0, y))
        y += strip.height + gap
    return sheet


def main() -> None:
    """Write every cropped picture."""
    TARGET.mkdir(parents=True, exist_ok=True)
    for number, name, mode in BROWSER_SHOTS:
        browser_picture(SOURCE / f"Screenshot ({number}).png", mode).save(TARGET / f"{name}.png", optimize=True)
    for number, name, right_edge, ranges in TERMINAL_SHOTS:
        terminal_picture(SOURCE / f"Screenshot ({number}).png", right_edge, ranges).save(TARGET / f"{name}.png", optimize=True)
    print(f"wrote {len(BROWSER_SHOTS) + len(TERMINAL_SHOTS)} pictures to {TARGET}")


if __name__ == "__main__":
    main()
