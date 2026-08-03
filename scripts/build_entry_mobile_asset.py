"""Compose the portrait entry artwork from the approved desktop master."""

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import median

from PIL import Image, ImageChops, ImageEnhance


def multiply_paste(canvas: Image.Image, layer: Image.Image, xy: tuple[int, int]) -> None:
    region = canvas.crop((xy[0], xy[1], xy[0] + layer.width, xy[1] + layer.height))
    canvas.paste(ImageChops.multiply(region, layer), xy)


def normalize_paper(layer: Image.Image, border: int = 20) -> Image.Image:
    """Map the source paper to white so only its ink darkens the new paper."""
    strips = (
        layer.crop((0, 0, layer.width, border)),
        layer.crop((0, layer.height - border, layer.width, layer.height)),
        layer.crop((0, 0, border, layer.height)),
        layer.crop((layer.width - border, 0, layer.width, layer.height)),
    )
    pixels = [pixel for strip in strips for pixel in strip.getdata()]
    paper = tuple(max(1, round(median(pixel[channel] for pixel in pixels))) for channel in range(3))
    channels = layer.split()
    normalized = [channel.point(lambda value, p=p: min(255, round(value * 255 / p))) for channel, p in zip(channels, paper)]
    return Image.merge("RGB", normalized)


def build(source_path: Path, output_path: Path) -> None:
    source = Image.open(source_path).convert("RGB")
    paper_patch = source.crop((820, 70, 1460, 510)).resize((1024, 1536), Image.Resampling.LANCZOS)
    canvas = Image.blend(Image.new("RGB", (1024, 1536), "#eee3cf"), paper_patch, 0.42)

    brand = normalize_paper(source.crop((238, 205, 820, 515))).resize((760, 405), Image.Resampling.LANCZOS)
    multiply_paste(canvas, brand, (178, 260))

    motto = normalize_paper(source.crop((112, 168, 226, 535)), border=10).resize((122, 393), Image.Resampling.LANCZOS)
    multiply_paste(canvas, motto, (52, 178))

    landscape = normalize_paper(source.crop((0, 515, source.width, source.height)), border=30).resize((1120, 371), Image.Resampling.LANCZOS)
    landscape = ImageEnhance.Contrast(landscape).enhance(0.93)
    multiply_paste(canvas, landscape, (-48, 1165))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.source, args.output)


if __name__ == "__main__":
    main()
