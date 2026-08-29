from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = Path(__file__).resolve().parent / "assets"
FONT_PATH = ROOT / "assets" / "fonts" / "NotoSansThai-SemiBold.ttf"


def build_icon() -> Image.Image:
    size = 1024
    image = Image.new("RGBA", (size, size), "#F8FAFC")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((72, 72, 952, 952), radius=180, fill="#0057D9")
    draw.rounded_rectangle((190, 128, 834, 896), radius=72, fill="#FFFFFF")
    draw.polygon(((650, 128), (834, 312), (650, 312)), fill="#DCEAFF")
    draw.rounded_rectangle((190, 676, 834, 896), radius=72, fill="#F97316")
    draw.rectangle((190, 676, 834, 824), fill="#F97316")

    font = ImageFont.truetype(str(FONT_PATH), 250)
    text = "SB"
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    draw.text(((size - text_width) / 2, 292), text, font=font, fill="#0057D9")
    return image


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    image = build_icon()
    image.save(ASSET_DIR / "StampBOX.png")
    image.save(
        ASSET_DIR / "StampBOX.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    image.save(ASSET_DIR / "StampBOX.icns")


if __name__ == "__main__":
    main()
