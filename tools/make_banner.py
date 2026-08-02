"""Generate the profile banner SVGs.

    pip install fonttools
    python3 tools/make_banner.py

Writes assets/banner-light.svg and assets/banner-dark.svg. Fonts are downloaded
once into .fonts/ (gitignored).

Every glyph is emitted as a <path>: GitHub serves README images through camo and
gives no font guarantees, so live <text> would fall back to whatever the viewer
happens to have. Outlines render identically everywhere at the cost of file size.

To restyle, edit the token dicts and TAGS below and re-run. Keep the accent fill
on exactly one tag — it is the only loud element in the design.
"""
import os
import urllib.request

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(REPO_ROOT, ".fonts")
OUT_DIR = os.path.join(REPO_ROOT, "assets")

FONTS = {
    "SpaceGrotesk": "https://raw.githubusercontent.com/google/fonts/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
    "JetBrainsMono": "https://raw.githubusercontent.com/google/fonts/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}

W, H = 1120, 230
TAG_W, TAG_H, TAG_GAP, TAG_Y = 118, 132, 14, 50
NOTCH = 26  # angled top-left corner, so the shape reads as a hang tag

# One tag per domain. The first one gets the accent fill.
TAGS = [
    ("RETAIL", "sql"),
    ("QUANT", "python"),
    ("ML", "sklearn"),
    ("NOTES", "mkdocs"),
]

LIGHT = dict(bg="#FAFAF7", ink="#16181D", muted="#6B6F76",
             accent="#FFC93C", teal="#2F6F6B", rule="#CFCBC0")
DARK = dict(bg="#0F1115", ink="#E8E6E1", muted="#8A9099",
            accent="#FFC93C", teal="#56A9A2", rule="#3D4450")


def font_file(name):
    os.makedirs(FONT_DIR, exist_ok=True)
    path = os.path.join(FONT_DIR, f"{name}.ttf")
    if not os.path.exists(path):
        print(f"downloading {name}")
        urllib.request.urlretrieve(FONTS[name], path)
    return path


def load(name, weight):
    font = instancer.instantiateVariableFont(
        TTFont(font_file(name)), {"wght": weight}
    )
    return font, font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm


def tag_path(x, y, w, h, n=NOTCH, r=5):
    """Hang-tag outline: square-ish body with the top-left corner cut away."""
    return (
        f"M{x + n} {y} H{x + w - r} A{r} {r} 0 0 1 {x + w} {y + r} "
        f"V{y + h - r} A{r} {r} 0 0 1 {x + w - r} {y + h} "
        f"H{x + r} A{r} {r} 0 0 1 {x} {y + h - r} V{y + n} Z"
    )


def text(face, s, size, x, y, fill, tracking=0.0, opacity=None):
    """Emit `s` as outline paths with the baseline origin at (x, y)."""
    font, gs, cmap, upem = face
    scale = size / upem
    hmtx = font["hmtx"]
    out, pen_x = [], 0.0
    for ch in s:
        gname = cmap.get(ord(ch))
        if gname is None:
            continue
        pen = SVGPathPen(gs, ntos=lambda v: f"{v:.0f}")
        gs[gname].draw(pen)
        d = pen.getCommands()
        if d.strip():
            out.append(
                f'<path d="{d}" transform="translate({x + pen_x * scale:.2f} {y:.2f}) '
                f'scale({scale:.6f} {-scale:.6f})" fill="{fill}"'
                + (f' opacity="{opacity}"' if opacity else "")
                + "/>"
            )
        pen_x += hmtx[gname][0] + tracking / scale
    return out


def build(c):
    display = load("SpaceGrotesk", 700)
    mono = load("JetBrainsMono", 500)
    p = [f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>']

    p += text(display, "SHANE WANG", 46, 48, 112, c["ink"], tracking=-1.4)
    p += text(mono, "retail analytics / quant research / machine learning",
              12.5, 50, 150, c["muted"])
    p += text(mono, "familymart data analyst · ntu econ ma · taipei",
              12.5, 50, 174, c["teal"])

    x0 = W - 48 - (len(TAGS) * TAG_W + (len(TAGS) - 1) * TAG_GAP)
    for i, (label, tool) in enumerate(TAGS):
        x = x0 + i * (TAG_W + TAG_GAP)
        lead = i == 0  # the day job is the one tag that gets the accent fill
        edge = c["ink"] if lead else c["rule"]
        on_tag = "#16181D" if lead else c["ink"]
        sub = "#16181D" if lead else c["muted"]
        p.append(
            f'<path d="{tag_path(x, TAG_Y, TAG_W, TAG_H)}" '
            f'fill="{c["accent"] if lead else "none"}" '
            f'stroke="{edge}" stroke-width="1.3" stroke-linejoin="round"/>'
        )
        p.append(
            f'<circle cx="{x + 21}" cy="{TAG_Y + 21}" r="4.5" fill="none" '
            f'stroke="{edge}" stroke-width="1.3"/>'
        )
        p += text(display, label, 18, x + 14, TAG_Y + 72, on_tag, tracking=-0.3)
        p.append(
            f'<line x1="{x + 14}" y1="{TAG_Y + 88}" x2="{x + TAG_W - 14}" '
            f'y2="{TAG_Y + 88}" stroke="{edge}" stroke-width="1" '
            f'opacity="{0.35 if lead else 1}"/>'
        )
        p += text(mono, tool, 10.5, x + 14, TAG_Y + 110, sub,
                  opacity="0.75" if lead else None)

    body = "\n  ".join(p)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="Shane Wang - retail analytics, quant research, machine learning">\n'
        f"  {body}\n</svg>\n"
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, colors in (("banner-light", LIGHT), ("banner-dark", DARK)):
        out = os.path.join(OUT_DIR, f"{name}.svg")
        with open(out, "w") as fh:
            fh.write(build(colors))
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
