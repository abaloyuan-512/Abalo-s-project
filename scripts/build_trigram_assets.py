"""Build exact raster assets for the eight Unicode trigram symbols."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ASSET_SIZE = 128
INK = (38, 39, 32, 255)
FONT_PATH = Path("C:/Windows/Fonts/seguisym.ttf")
OUTPUT_DIR = Path(__file__).parents[1] / "sites" / "hosted-app" / "public" / "trigrams"

TRIGRAMS: tuple[tuple[str, str], ...] = (
    ("qian", "☰"),
    ("dui", "☱"),
    ("li", "☲"),
    ("zhen", "☳"),
    ("xun", "☴"),
    ("kan", "☵"),
    ("gen", "☶"),
    ("kun", "☷"),
)


def build_asset(name: str, symbol: str) -> Path:
    """Render one canonical Unicode trigram to a transparent PNG."""
    image = Image.new("RGBA", (ASSET_SIZE, ASSET_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT_PATH), 102)
    bounds = draw.textbbox((0, 0), symbol, font=font)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    position = ((ASSET_SIZE - width) / 2 - bounds[0], (ASSET_SIZE - height) / 2 - bounds[1] - 2)
    draw.text(position, symbol, font=font, fill=INK)
    output = OUTPUT_DIR / f"{name}.png"
    image.save(output, optimize=True)
    return output


def main() -> None:
    """Create all eight trigram assets in the hosted app."""
    if not FONT_PATH.is_file():
        raise FileNotFoundError(f"Required Unicode symbol font not found: {FONT_PATH}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, symbol in TRIGRAMS:
        build_asset(name, symbol)


if __name__ == "__main__":
    main()
