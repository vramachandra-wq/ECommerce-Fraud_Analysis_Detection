"""Generate a minimal Metro Cart architecture diagram."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images" / "architecture_diagram.png"

W, H = 900, 640
BG = (252, 252, 253)
INK = (15, 23, 42)
MUTED = (100, 116, 139)
WHITE = (255, 255, 255)
BLUE = (37, 99, 235)
BLUE_DK = (30, 64, 175)
SKY = (2, 132, 199)
AMBER = (217, 119, 6)
TEAL = (13, 148, 136)
VIOLET = (124, 58, 237)
PINK = (219, 39, 119)
LINE = (148, 163, 184)


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


def center_text(draw, cx, cy, text, fnt, fill=INK):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2), text, font=fnt, fill=fill)


def pill(draw, x, y, w, h, title, outline):
    draw.rounded_rectangle(
        (x, y, x + w, y + h), radius=h // 2, fill=(239, 246, 255), outline=outline, width=2
    )
    center_text(draw, x + w / 2, y + h / 2, title, font(14, True), outline)


def box(draw, x, y, w, h, title, subtitle, outline):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=14, fill=WHITE, outline=outline, width=2)
    center_text(draw, x + w / 2, y + h / 2 - 10, title, font(17, True), INK)
    center_text(draw, x + w / 2, y + h / 2 + 14, subtitle, font(12), MUTED)


def down_arrow(draw, x, y1, y2):
    draw.line([(x, y1), (x, y2)], fill=LINE, width=2)
    draw.polygon([(x, y2), (x - 7, y2 - 8), (x + 7, y2 - 8)], fill=LINE)


def main():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    center_text(draw, W / 2, 36, "Metro Cart Architecture", font(26, True), BLUE_DK)

    # Users
    pill(draw, 160, 70, 130, 36, "Customer", BLUE)
    pill(draw, 385, 70, 130, 36, "Analyst", BLUE)
    pill(draw, 610, 70, 130, 36, "Admin", BLUE)

    down_arrow(draw, 225, 106, 140)
    down_arrow(draw, 450, 106, 140)
    draw.line([(740, 124), (450, 124)], fill=LINE, width=2)
    down_arrow(draw, 740, 106, 124)

    # Portals
    box(draw, 90, 145, 280, 68, "Customer Portal", "Streamlit", BLUE)
    box(draw, 420, 145, 390, 68, "Internal Portal", "Streamlit", BLUE_DK)

    down_arrow(draw, 230, 213, 250)
    down_arrow(draw, 615, 213, 250)

    # Middle layer
    box(draw, 90, 255, 350, 72, "Fraud Engine", "12 rules · score & decide", AMBER)
    box(draw, 480, 255, 330, 72, "FastAPI", "persist · review · config", SKY)

    down_arrow(draw, 265, 327, 365)
    down_arrow(draw, 645, 327, 365)

    # Database
    box(draw, 200, 370, 500, 72, "PostgreSQL", "orders · rules · audit", TEAL)

    # Externals — no connecting lines
    box(draw, 160, 480, 240, 60, "Groq", "AI chatbot", VIOLET)
    box(draw, 500, 480, 240, 60, "Power BI", "reports", PINK)

    center_text(
        draw,
        W / 2,
        580,
        "Evaluate → Save → Review or auto-approve → Audit",
        font(13),
        MUTED,
    )
    center_text(
        draw,
        W / 2,
        610,
        "Python · Streamlit · FastAPI · PostgreSQL",
        font(12),
        LINE,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
