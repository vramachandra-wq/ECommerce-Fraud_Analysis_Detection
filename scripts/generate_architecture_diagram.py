"""Generate Metro Cart architecture diagram (current FastAPI + portals layout)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images" / "architecture_diagram.png"

W, H = 1180, 720
BG = (32, 32, 32)
PANEL = (42, 42, 42)
PANEL_EDGE = (120, 120, 120)
BOX = (52, 52, 52)
BOX_EDGE = (170, 170, 170)
INK = (245, 245, 245)
MUTED = (180, 180, 180)
LINE = (190, 190, 190)


def font(size: int, bold: bool = False):
    for path in (
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_label(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, *, bold=False, fill=INK, size=16):
    draw.text((x, y), text, font=font(size, bold), fill=fill)


def panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=PANEL, outline=PANEL_EDGE, width=2)
    draw_label(draw, x + 16, y + 12, title, bold=True, size=18)


def inner_box(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, subtitle: str = ""):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=BOX, outline=BOX_EDGE, width=2)
    tw, th = text_size(draw, title, font(15, True))
    cx = x + w / 2
    if subtitle:
        draw.text((cx - tw / 2, y + h / 2 - 16), title, font=font(15, True), fill=INK)
        sw, _ = text_size(draw, subtitle, font(12))
        draw.text((cx - sw / 2, y + h / 2 + 6), subtitle, font=font(12), fill=MUTED)
    else:
        draw.text((cx - tw / 2, y + h / 2 - th / 2), title, font=font(15, True), fill=INK)


def arrow(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]]):
    draw.line(points, fill=LINE, width=2)
    x0, y0 = points[-2]
    x1, y1 = points[-1]
    dx, dy = x1 - x0, y1 - y0
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    left = (x1 - 10 * ux + 6 * uy, y1 - 10 * uy - 6 * ux)
    right = (x1 - 10 * ux - 6 * uy, y1 - 10 * uy + 6 * ux)
    draw.polygon([(x1, y1), left, right], fill=LINE)


def cylinder(draw: ImageDraw.ImageDraw, cx: int, cy: int, rw: int = 54, rh: int = 18, body: int = 70):
    # Top ellipse
    draw.ellipse((cx - rw, cy - rh, cx + rw, cy + rh), outline=BOX_EDGE, width=2)
    # Sides
    draw.line([(cx - rw, cy), (cx - rw, cy + body)], fill=BOX_EDGE, width=2)
    draw.line([(cx + rw, cy), (cx + rw, cy + body)], fill=BOX_EDGE, width=2)
    # Bottom ellipse
    draw.ellipse((cx - rw, cy + body - rh, cx + rw, cy + body + rh), outline=BOX_EDGE, width=2)
    label = "master schema"
    tw, th = text_size(draw, label, font(13, True))
    draw.text((cx - tw / 2, cy + body / 2 - th / 2), label, font=font(13, True), fill=INK)


def main():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # --- Panels ---
    # Left: portals
    panel(draw, 40, 70, 280, 300, "Web Portals")
    inner_box(draw, 70, 120, 220, 80, "Customer Shop", "/shop/ · :8000")
    inner_box(draw, 70, 240, 220, 80, "Analyst Portal", "/portal/ · React")

    # Middle stack
    panel(draw, 380, 40, 360, 170, "Fraud Engine")
    inner_box(draw, 410, 85, 140, 90, "evaluate_order")
    inner_box(draw, 580, 85, 140, 90, "12 Rules", "R001–R012")
    arrow(draw, [(550, 130), (580, 130)])

    panel(draw, 380, 240, 360, 150, "FastAPI :8000")
    inner_box(draw, 410, 290, 300, 70, "Orders / Admin / Portal APIs", "scheduler · SSO · audit")

    panel(draw, 380, 420, 360, 140, "Groq LLM")
    inner_box(draw, 410, 470, 300, 60, "NL-to-SQL Chatbot")

    panel(draw, 380, 580, 360, 100, "SSO IdP :8080")
    inner_box(draw, 410, 625, 300, 40, "OIDC · realm metro-cart")

    # Right: database
    panel(draw, 800, 180, 340, 320, "PostgreSQL")
    cylinder(draw, 970, 280)
    draw_label(draw, 860, 430, "orders · rules · hits · audit", size=13, fill=MUTED)
    draw_label(draw, 880, 455, "analysts · blacklists · chat", size=13, fill=MUTED)

    # --- Flows ---
    # Customer shop → Fraud Engine + FastAPI
    arrow(draw, [(290, 160), (340, 160), (340, 110), (380, 110)])
    arrow(draw, [(290, 175), (340, 175), (340, 325), (380, 325)])

    # Analyst portal → FastAPI + Groq + SSO
    arrow(draw, [(290, 270), (340, 270), (340, 340), (380, 340)])
    arrow(draw, [(290, 290), (340, 290), (340, 500), (380, 500)])
    arrow(draw, [(180, 320), (180, 645), (380, 645)])

    # Engine / API / Chatbot → Postgres
    arrow(draw, [(740, 130), (780, 130), (780, 280), (800, 280)])
    arrow(draw, [(740, 325), (780, 325), (780, 320), (800, 320)])
    arrow(draw, [(740, 500), (780, 500), (780, 360), (800, 360)])

    # SSO note (auth only — no DB arrow)
    draw_label(
        draw,
        40,
        400,
        "Auth: password + SSO cookie sessions",
        size=13,
        fill=MUTED,
    )
    draw_label(
        draw,
        40,
        430,
        "Auto-approval scheduler every 30 min",
        size=13,
        fill=MUTED,
    )
    draw_label(
        draw,
        40,
        640,
        "Python · FastAPI · React · PostgreSQL · SSO · Groq",
        size=13,
        fill=MUTED,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
