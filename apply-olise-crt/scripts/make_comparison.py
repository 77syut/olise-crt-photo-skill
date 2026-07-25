#!/usr/bin/env python3
"""Create a clean before/after sheet without cropping either image."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--title", default="SCENE TEST")
    return parser.parse_args()


def contain(image, size):
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return image


def main():
    args = parse_args()
    width, height = 1440, 900
    margin, gap, header = 42, 32, 78
    panel_width = (width - margin * 2 - gap) // 2
    panel_height = height - header - margin
    canvas = Image.new("RGB", (width, height), (12, 16, 19))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 22), args.title, fill=(218, 229, 230))

    with Image.open(args.before) as source:
        before = contain(source, (panel_width, panel_height - 42))
    with Image.open(args.after) as result:
        after = contain(result, (panel_width, panel_height - 42))

    for index, (label, image) in enumerate((("BEFORE", before), ("AFTER", after))):
        x0 = margin + index * (panel_width + gap)
        draw.text((x0, header), label, fill=(158, 181, 184))
        x = x0 + (panel_width - image.width) // 2
        y = header + 34 + (panel_height - 42 - image.height) // 2
        canvas.paste(image, (x, y))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, quality=94, subsampling=1)


if __name__ == "__main__":
    main()
