#!/usr/bin/env python3
"""news-image-20261120: sum up Friday 20 November 2026 in one image.

A pure-standard-library renderer (no PIL, no network, no fonts on disk).
It draws a newspaper front page -- masthead, lead story, five more stories
and an "also today" strip -- onto a 1024x1024 canvas with a hand-written
5x7 bitmap font, then encodes the PNG by hand (zlib + struct) so the
program runs identically in the make.fun sandbox (Python 3.13, stdlib
only) and writes deterministic bytes to /output/entry.png.

Run locally:
    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 232)   # newsprint off-white
INK = (17, 17, 17)        # near-black ink
NAVY = (18, 38, 76)       # masthead band
NAVY_LT = (38, 64, 110)
RED = (178, 34, 34)       # headline accent / flags
GOLD = (212, 160, 23)
SKY_NIGHT = (16, 24, 48)  # Kyiv night sky
SKY_DUSK = (52, 68, 110)
RIVER = (38, 78, 128)
FIRE = (240, 140, 32)
FIRE_Y = (250, 205, 60)
GREY = (120, 120, 118)
GREY_LT = (222, 218, 205)
BLUE = (30, 90, 168)
GREEN = (34, 120, 70)
TEAL = (14, 110, 110)
WHITE = (255, 255, 255)
CREAM = (255, 248, 220)

# ---------------------------------------------------------------- 5x7 font
# Every glyph is 7 rows of 5 cells, '#' = ink, '.' = empty. All copy is
# upper-cased before drawing, so only capitals, digits and punctuation
# are needed. Drawn at integer scales (2, 3, 4, 6) for crisp edges.
FONT = {
    "A": (" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "B": ("#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "),
    "C": (" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"),
    "D": ("###  ", "#  # ", "#   #", "#   #", "#   #", "#  # ", "###  "),
    "E": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"),
    "F": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "),
    "G": (" ####", "#    ", "#    ", "# ###", "#   #", "#   #", " ### "),
    "H": ("#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "I": (" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "J": ("  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "),
    "K": ("#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"),
    "L": ("#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"),
    "M": ("#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"),
    "N": ("#   #", "##  #", "##  #", "# # #", "#  ##", "#  ##", "#   #"),
    "O": (" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "P": ("#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "),
    "Q": (" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"),
    "R": ("#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"),
    "S": (" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "),
    "U": ("#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "V": ("#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "),
    "W": ("#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"),
    "X": ("#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"),
    "Y": ("#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "),
    "Z": ("#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"),
    "0": (" ### ", "#  ##", "# # #", "##  #", "#   #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"),
    "3": ("#### ", "    #", "    #", " ### ", "    #", "    #", "#### "),
    "4": ("   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "),
    "5": ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    "6": (" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "   # ", "  #  ", "  #  ", "  #  "),
    "8": (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    "9": (" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "),
    " ": ("     ", "     ", "     ", "     ", "     ", "     ", "     "),
    ".": ("     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "),
    ",": ("     ", "     ", "     ", "     ", "     ", " ##  ", " #   "),
    ":": ("     ", " ##  ", " ##  ", "     ", " ##  ", " ##  ", "     "),
    ";": ("     ", " ##  ", " ##  ", "     ", " ##  ", " ##  ", " #   "),
    "'": ("  #  ", "  #  ", "  #  ", "     ", "     ", "     ", "     "),
    "-": ("     ", "     ", "     ", "#####", "     ", "     ", "     "),
    "(": ("   # ", "  #  ", " #   ", " #   ", " #   ", "  #  ", "   # "),
    ")": (" #   ", "  #  ", "   # ", "   # ", "   # ", "  #  ", " #   "),
    "/": ("    #", "   # ", "   # ", "  #  ", "  #  ", " #   ", "#    "),
    "&": (" ##  ", "#  # ", "#  # ", " #   ", "# # #", "#  # ", " ## #"),
    "%": ("#   #", "#  # ", "    #", "   # ", "  #  ", " #  #", "#   #"),
    "+": ("     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "),
    "!": ("  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "),
    "?": (" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "),
    "$": ("  #  ", " ####", "# # #", " ### ", "  # #", "#### ", "  #  "),
    "=": ("     ", "     ", "#####", "     ", "#####", "     ", "     "),
    '"': (" # # ", " # # ", "     ", "     ", "     ", "     ", "     "),
    "*": ("     ", " # # ", "  #  ", "#####", "  #  ", " # # ", "     "),
    "#": (" # # ", " # # ", "#####", " # # ", "#####", " # # ", " # # "),
    ">": ("#    ", " #   ", "  #  ", "   # ", "  #  ", " #   ", "#    "),
    "<": ("    #", "   # ", "  #  ", " #   ", "  #  ", "   # ", "    #"),
}


def text_width(text, scale):
    """Pixel width of upper-cased text at the given integer scale."""
    return len(text) * 6 * scale - scale


def wrap_text(text, scale, max_w):
    """Wrap upper-cased text into lines fitting max_w pixels."""
    max_chars = max(1, (max_w + scale) // (6 * scale))
    words = text.upper().split(" ")
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            # A single over-long word is hard-split.
            while len(word) > max_chars:
                lines.append(word[:max_chars])
                word = word[max_chars:]
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w=W, h=H, bg=PAPER):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def set_px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.px[o], self.px[o + 1], self.px[o + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            o = self._off(x0, yy)
            self.px[o:o + len(row)] = row

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, w=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        r = w // 2
        while True:
            self.fill_rect(x0 - r, y0 - r, w, w, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def filled_circle(self, cx, cy, r, c):
        import math
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def circle(self, cx, cy, r, c, t=2):
        import math
        for a in range(0, 360):
            rad = math.radians(a)
            self.fill_rect(int(cx + r * math.cos(rad)) - t // 2,
                           int(cy + r * math.sin(rad)) - t // 2, t, t, c)

    def filled_ellipse(self, cx, cy, rx, ry, c):
        import math
        for dy in range(-ry, ry + 1):
            dx = int(rx * math.sqrt(max(0.0, 1.0 - (dy * dy) / float(ry * ry))))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def polygon(self, points, c):
        """Scanline fill of a simple polygon (list of (x, y))."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[i]), y, max(1, int(xs[i + 1]) - int(xs[i])), 1, c)

    def starburst(self, cx, cy, r_out, r_in, spikes, c):
        import math
        pts = []
        for i in range(spikes * 2):
            r = r_out if i % 2 == 0 else r_in
            a = math.pi * i / spikes - math.pi / 2
            pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
        self.polygon(pts, c)

    def text(self, x, y, s, scale, c):
        """Draw upper-cased text; returns the pixel width drawn."""
        s = s.upper()
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT["?"])
            for row, bits in enumerate(glyph):
                for col, bit in enumerate(bits):
                    if bit == "#":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, c)
            cx += 6 * scale
        return cx - x - scale

    def text_centred(self, cx, y, s, scale, c):
        w = text_width(s.upper(), scale)
        self.text(cx - w // 2, y, s, scale, c)
        return w

    def para(self, x, y, s, scale, max_w, c, leading=None):
        """Wrapped paragraph; returns y just below the last line."""
        lh = leading if leading is not None else 9 * scale
        for line in wrap_text(s, scale, max_w):
            self.text(x, y, line, scale, c)
            y += lh
        return y


# ---------------------------------------------------------------- PNG encode
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png


# ------------------------------------------------------------------- art
def draw_flag_us(cv, x, y, w, h):
    stripe = max(1, h // 13)
    for i in range(13):
        cv.fill_rect(x, y + i * stripe, w, stripe,
                     RED if i % 2 == 0 else WHITE)
    cv.fill_rect(x, y, int(w * 0.4), stripe * 7, NAVY)
    for r in range(4):
        for col in range(5):
            cv.set_px(x + 6 + col * 8, y + 3 + r * 5, WHITE)


def draw_flag_cn(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, RED)
    cv.starburst(x + w // 5, y + h // 4, 7, 3, 5, GOLD)
    for dx, dy in ((14, 2), (20, 8), (20, 16), (14, 22)):
        cv.starburst(x + dx, y + dy, 3, 1, 5, GOLD)


def draw_flag_ru(cv, x, y, w, h):
    third = max(1, h // 3)
    cv.fill_rect(x, y, w, third, WHITE)
    cv.fill_rect(x, y + third, w, third, BLUE)
    cv.fill_rect(x, y + 2 * third, w, h - 2 * third, RED)


def draw_flag_gb(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, NAVY)
    cv.fill_rect(x, y + h // 3, w, h // 3, WHITE)
    cv.fill_rect(x + w // 3, y, w // 3, h, WHITE)
    cv.fill_rect(x, y + h // 2 - 2, w, 4, RED)
    cv.fill_rect(x + w // 2 - 2, y, 4, h, RED)


def draw_flag_eu(cv, x, y, w, h):
    import math
    cv.fill_rect(x, y, w, h, NAVY)
    for i in range(12):
        a = 2 * math.pi * i / 12 - math.pi / 2
        sx = x + w // 2 + int(0.32 * w * math.cos(a))
        sy = y + h // 2 + int(0.32 * h * math.sin(a))
        cv.starburst(sx, sy, 3, 1, 5, GOLD)


def draw_kyiv(cv, x, y, w, h):
    """Night skyline over the Dnipro: bridges, blasts, missile trails."""
    cv.fill_rect(x, y, w, h, SKY_NIGHT)
    # stars
    for sx, sy in ((18, 14), (60, 30), (120, 10), (180, 26), (240, 12),
                   (300, 32), (350, 16), (90, 44), (210, 48), (330, 46)):
        cv.set_px(x + sx, y + sy, WHITE)
        cv.set_px(x + sx + 1, y + sy, WHITE)
    # missile trails with warhead dots
    cv.line(x + 40, y + 8, x + 130, y + 78, FIRE_Y, 2)
    cv.line(x + 330, y + 4, x + 250, y + 66, FIRE_Y, 2)
    cv.filled_circle(x + 130, y + 78, 3, FIRE_Y)
    cv.filled_circle(x + 250, y + 66, 3, FIRE_Y)
    # skyline silhouettes with lit windows
    buildings = [(0, 96, 46, 84), (50, 76, 40, 104), (94, 106, 52, 74),
                 (150, 66, 38, 114), (192, 96, 44, 84), (240, 70, 40, 110),
                 (284, 100, 46, 80), (334, 82, 42, 98)]
    for bx, by, bw, bh in buildings:
        cv.fill_rect(x + bx, y + by, bw, bh, (8, 12, 26))
        for wy in range(by + 8, by + bh - 6, 12):
            for wx in range(bx + 6, bx + bw - 6, 12):
                if (wx * 7 + wy * 3) % 5:
                    cv.fill_rect(x + wx, y + wy, 4, 5, GOLD)
    ground = y + h - 58
    cv.fill_rect(x, y + ground - y, w, 58, (10, 14, 30))
    # river
    cv.fill_rect(x, ground + 22, w, h - (ground + 22 - y), RIVER)
    cv.line(x + 10, ground + 34, x + w - 10, ground + 34, (90, 140, 190), 2)
    cv.line(x + 40, ground + 46, x + w - 40, ground + 46, (90, 140, 190), 2)
    # three bridges across the river
    for bx in (30, 150, 268):
        cv.fill_rect(x + bx, ground + 6, 84, 5, (150, 150, 148))
        cv.line(x + bx + 8, ground + 6, x + bx + 42, ground - 16,
                (150, 150, 148), 2)
        cv.line(x + bx + 76, ground + 6, x + bx + 42, ground - 16,
                (150, 150, 148), 2)
    # explosion bursts
    cv.starburst(x + 110, y + 108, 26, 12, 9, FIRE)
    cv.starburst(x + 110, y + 108, 15, 7, 9, FIRE_Y)
    cv.starburst(x + 300, y + 118, 20, 9, 9, FIRE)
    cv.starburst(x + 300, y + 118, 11, 5, 9, FIRE_Y)
    cv.starburst(x + 210, y + 92, 14, 6, 8, FIRE)
    # smoke
    cv.filled_circle(x + 110, y + 84, 12, (70, 70, 74))
    cv.filled_circle(x + 122, y + 78, 9, (90, 90, 94))
    cv.filled_circle(x + 300, y + 98, 10, (70, 70, 74))


def draw_summit(cv, x, y, w, h):
    """Three flags over a table: the Shenzhen trilateral."""
    cv.fill_rect(x, y, w, h, (232, 226, 208))
    cv.fill_rect(x, y, w, 10, GOLD)
    fw, fh = 84, 52
    gap = (w - 3 * fw) // 4
    draw_flag_us(cv, x + gap, y + 26, fw, fh)
    draw_flag_cn(cv, x + 2 * gap + fw, y + 26, fw, fh)
    draw_flag_ru(cv, x + 3 * gap + 2 * fw, y + 26, fw, fh)
    for fx in (x + gap, x + 2 * gap + fw, x + 3 * gap + 2 * fw):
        cv.fill_rect(fx + fw // 2 - 2, y + 78, 4, 34, INK)
    # table
    cv.fill_rect(x + 14, y + 112, w - 28, 10, (122, 82, 40))
    cv.fill_rect(x + 26, y + 122, 8, 26, (90, 60, 28))
    cv.fill_rect(x + w - 34, y + 122, 8, 26, (90, 60, 28))
    # three seated figures (simple silhouettes)
    for fx in (x + gap + fw // 2, x + 2 * gap + fw + fw // 2,
               x + 3 * gap + 2 * fw + fw // 2):
        cv.filled_circle(fx, y + 126, 10, NAVY)
        cv.fill_rect(fx - 12, y + 136, 24, 20, NAVY)
    # handshake star in the middle
    cv.starburst(x + w // 2, y + 96, 12, 5, 5, GOLD)


def draw_court(cv, x, y, w, h):
    """Scales of justice before a courthouse colonnade."""
    cv.fill_rect(x, y, w, h, (228, 222, 206))
    # colonnade
    for cx in range(x + 18, x + w - 18, 52):
        cv.fill_rect(cx, y + 16, 16, 52, (180, 172, 148))
        cv.fill_rect(cx - 3, y + 12, 22, 6, (160, 152, 128))
        cv.fill_rect(cx - 3, y + 68, 22, 6, (160, 152, 128))
    cv.fill_rect(x + 10, y + 6, w - 20, 8, (160, 152, 128))
    # scales
    cx, top = x + w // 2, y + 82
    cv.fill_rect(cx - 2, top, 4, 40, INK)
    cv.line(cx - 52, top + 6, cx + 52, top + 6, INK, 3)
    cv.line(cx - 52, top + 6, cx - 52, top + 26, INK, 2)
    cv.line(cx + 52, top + 6, cx + 52, top + 26, INK, 2)
    cv.polygon([(cx - 66, top + 26), (cx - 38, top + 26), (cx - 52, top + 42)],
               GOLD)
    cv.polygon([(cx + 38, top + 26), (cx + 66, top + 26), (cx + 52, top + 42)],
               GOLD)
    cv.filled_circle(cx, top, 5, INK)
    cv.fill_rect(x + 10, y + h - 10, w - 20, 6, (160, 152, 128))


def draw_markets(cv, x, y, w, h):
    """A plunging chart over a trading floor strip."""
    cv.fill_rect(x, y, w, h, (232, 228, 222))
    # grid
    for gy in range(y + 16, y + h - 40, 24):
        cv.line(x + 12, gy, x + w - 12, gy, (200, 198, 190), 1)
    # axes
    cv.line(x + 16, y + 14, x + 16, y + h - 34, INK, 2)
    cv.line(x + 16, y + h - 34, x + w - 14, y + h - 34, INK, 2)
    # falling line: IPO spike, then the slide (stays above the x-axis)
    pts = [(24, 30), (62, 22), (100, 38), (138, 56), (176, 72),
           (214, 80), (252, 86), (282, 90)]
    for i in range(len(pts) - 1):
        cv.line(x + pts[i][0], y + pts[i][1], x + pts[i + 1][0],
                y + pts[i + 1][1], RED, 4)
    cv.filled_circle(x + 62, y + 22, 6, GREEN)
    cv.text(x + 20, y + h - 26, "NIKKEI -4.8%", 2, RED)


def draw_protest(cv, x, y, w, h):
    """A crowd with placards under a pale sky."""
    cv.fill_rect(x, y, w, h, (226, 232, 240))
    cv.fill_rect(x, y + h - 46, w, 46, (120, 118, 110))
    # placards
    for px, ph, lab in ((26, 14, "FAIR"), (120, 10, "HOMES"), (214, 16, "PAY")):
        cv.fill_rect(x + px, y + ph, 66, 34, WHITE)
        cv.rect(x + px, y + ph, 66, 34, INK, 2)
        cv.text(x + px + 6, y + ph + 9, lab, 2, INK)
        cv.fill_rect(x + px + 30, y + ph + 34, 4, 40, INK)
    # crowd: one full row of heads and shoulders, a second row of heads
    for i in range(7):
        hx = x + 24 + i * (w - 48) // 6
        cv.filled_circle(hx, y + 100, 11, NAVY)
        cv.filled_ellipse(hx, y + 119, 17, 10, NAVY)
    for i in range(9):
        hx = x + 18 + i * (w - 36) // 8
        cv.filled_circle(hx, y + 124, 9, TEAL)


def draw_mobility(cv, x, y, w, h):
    """Union Jack and EU stars circle, joined by an arrow."""
    cv.fill_rect(x, y, w, h, (232, 226, 208))
    draw_flag_gb(cv, x + 24, y + 30, 110, 62)
    draw_flag_eu(cv, x + w - 134, y + 30, 110, 62)
    cv.line(x + 140, y + 61, x + w - 150, y + 61, GREEN, 5)
    cv.polygon([(x + w - 150, y + 49), (x + w - 150, y + 73),
                (x + w - 128, y + 61)], GREEN)
    # two walking figures (busts, inside the art area)
    for fx, col in ((x + 70, NAVY), (x + w - 80, NAVY)):
        cv.filled_circle(fx, y + 102, 9, col)
        cv.fill_rect(fx - 11, y + 111, 22, 17, col)


# ------------------------------------------------------------------ layout
def rule(cv, y):
    cv.fill_rect(16, y, W - 32, 3, INK)


def kicker(cv, x, y, s, c=RED):
    cv.text(x, y, s, 2, c)
    return y + 20


def panel(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, h, INK, 2)


def build():
    cv = Canvas()
    # ---- masthead
    cv.fill_rect(0, 0, W, 108, NAVY)
    cv.fill_rect(0, 104, W, 4, GOLD)
    cv.text_centred(W // 2, 8, "THE WORLD IN ONE DAY", 6, WHITE)
    cv.text_centred(W // 2, 54, "FRIDAY 20 NOVEMBER 2026", 3, GOLD)
    cv.text_centred(W // 2, 82, "ONE DAY  -  ONE IMAGE  -  THE WORLD'S NEWS",
                    2, (200, 208, 224))

    # ---- lead story: Kyiv overnight attack
    ly, lh = 118, 296
    panel(cv, 16, ly, W - 32, lh)
    draw_kyiv(cv, 28, ly + 12, 560, lh - 24)
    tx = 612
    kicker(cv, tx, ly + 16, "UKRAINE  -  LEAD STORY")
    y = cv.para(tx, ly + 40, "KYIV HIT BY 100 MISSILES OVERNIGHT", 4, 380,
                RED, 38)
    y += 6
    y = cv.para(tx, y, "100+ MISSILES, 400 DRONES.", 2, 380, INK, 20)
    y = cv.para(tx, y, "3 KYIV BRIDGES DAMAGED.", 2, 380, INK, 20)
    y = cv.para(tx, y, "POWER GRID 'EXTREMELY CRITICAL'.", 2, 380, INK, 20)
    y = cv.para(tx, y, "ALLIES MEET IN BERLIN TODAY.", 2, 380, INK, 20)
    cv.fill_rect(tx, y + 6, 380, 3, RED)
    cv.text(tx, y + 16, "8 DEAD  -  28 INJURED", 2, RED)

    # ---- row 2: summit + world court
    ry, rh = 426, 246
    pw = (W - 32 - 16) // 2
    # summit (left)
    panel(cv, 16, ry, pw, rh)
    draw_summit(cv, 28, ry + 12, pw - 24, 148)
    kicker(cv, 28, ry + 166, "DIPLOMACY  -  SHENZHEN, CHINA")
    y = cv.para(28, ry + 186, "TRUMP, XI AND PUTIN SIGN PEACE DECLARATION",
                2, pw - 24, INK, 18)
    cv.para(28, y + 2, "NO UKRAINE BREAKTHROUGH.",
            2, pw - 24, INK, 18)
    # court (right)
    cx2 = 16 + pw + 16
    panel(cv, cx2, ry, pw, rh)
    draw_court(cv, cx2 + 12, ry + 12, pw - 24, 148)
    kicker(cv, cx2 + 12, ry + 166, "JUSTICE  -  THE HAGUE")
    y = cv.para(cx2 + 12, ry + 186, "WORLD COURT: MYANMAR COMMITTED GENOCIDE",
                2, pw - 24, INK, 18)
    cv.para(cx2 + 12, y + 2, "FIRST SUCH RULING AGAINST A STATE.",
            2, pw - 24, INK, 18)

    # ---- row 3: markets, protests, mobility
    ty, th = 684, 224
    tw = (W - 32 - 32) // 3
    x3 = [16, 16 + tw + 16, 16 + 2 * (tw + 16)]
    panel(cv, x3[0], ty, tw, th)
    draw_markets(cv, x3[0] + 10, ty + 10, tw - 20, 128)
    kicker(cv, x3[0] + 12, ty + 144, "ECONOMY")
    y = cv.para(x3[0] + 12, ty + 164, "AI FEARS HIT MARKETS", 2, tw - 24,
                INK, 18)
    cv.para(x3[0] + 12, y + 2, "ANTHROPIC +17% IN RECORD IPO.", 2, tw - 24,
            INK, 18)
    panel(cv, x3[1], ty, tw, th)
    draw_protest(cv, x3[1] + 10, ty + 10, tw - 20, 128)
    kicker(cv, x3[1] + 12, ty + 144, "EUROPE")
    y = cv.para(x3[1] + 12, ty + 164, "YOUTH TAKE TO STREETS", 2, tw - 24,
                INK, 18)
    cv.para(x3[1] + 12, y + 2, "PROTESTS IN 25+ COUNTRIES.",
            2, tw - 24, INK, 18)
    panel(cv, x3[2], ty, tw, th)
    draw_mobility(cv, x3[2] + 10, ty + 10, tw - 20, 128)
    kicker(cv, x3[2] + 12, ty + 144, "UK  -  EU")
    y = cv.para(x3[2] + 12, ty + 164, "YOUTH MOBILITY DEAL AGREED", 2, tw - 24,
                INK, 18)
    cv.para(x3[2] + 12, y + 2, "LIVE AND WORK ABROAD.", 2, tw - 24, INK, 18)

    # ---- also-today strip
    ay = 916
    cv.fill_rect(16, ay, W - 32, 76, NAVY)
    cv.text(28, ay + 10, "ALSO TODAY", 2, GOLD)
    cv.para(28, ay + 34,
            "TRUMP PARDONS PETE ROSE  -  POLAND LIFTS AIR ALERT  -  "
            "KENYA'S LAST EBOLA PATIENT GOES HOME  -  SPAIN STRIKES  -  "
            "LAGARDE LEAVES ECB",
            2, W - 56, WHITE, 20)
    cv.text_centred(W // 2, 1000, "FRIDAY 20 NOVEMBER 2026  -  THE DAY IN ONE IMAGE",
                    2, GREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(build())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
