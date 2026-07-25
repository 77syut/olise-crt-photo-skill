#!/usr/bin/env python3
"""Create a rounded README-ready before/after comparison card."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--title", default="SCENE TEST")
    parser.add_argument("--mode", default="STATIC")
    parser.add_argument("--before-label", default="ORIGINAL")
    parser.add_argument("--after-label", default="OLISE CRT")
    return parser.parse_args()


def cover(image, size):
    image = ImageOps.exif_transpose(image).convert("RGB")
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def font(size, bold=False):
    candidates = [
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded_card(image, size, radius=34):
    image = cover(image, size)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1),
        radius=radius,
        fill=255,
    )
    card = Image.new("RGBA", size, (0, 0, 0, 0))
    card.paste(image, (0, 0), mask)
    return card, mask


def main():
    args = parse_args()
    width, height = 1400, 820
    card_size = (560, 560)
    gap = 76
    left = (width - card_size[0] * 2 - gap) // 2
    top = 142
    canvas = Image.new("RGB", (width, height), (246, 243, 236))
    draw = ImageDraw.Draw(canvas)
    title_font = font(31, bold=True)
    label_font = font(20, bold=True)
    meta_font = font(17, bold=True)
    draw.text((left, 43), args.title.upper(), font=title_font, fill=(29, 37, 38))

    with Image.open(args.before) as source:
        before, before_mask = rounded_card(source, card_size)
    with Image.open(args.after) as result:
        after, after_mask = rounded_card(result, card_size)

    for index, (label, image, mask) in enumerate(
        (
            (args.before_label, before, before_mask),
            (args.after_label, after, after_mask),
        )
    ):
        x = left + index * (card_size[0] + gap)
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_shape = Image.new("L", card_size, 0)
        shadow_shape.paste(mask)
        shadow_shape = shadow_shape.filter(ImageFilter.GaussianBlur(radius=16))
        shadow_layer = Image.new("RGBA", card_size, (20, 29, 31, 72))
        shadow_layer.putalpha(shadow_shape.point(lambda value: int(value * 0.30)))
        shadow.alpha_composite(shadow_layer, (x + 8, top + 13))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow)
        canvas.alpha_composite(image, (x, top))
        draw = ImageDraw.Draw(canvas)
        draw.text((x, top - 38), label, font=label_font, fill=(80, 92, 93))

    badge_text = args.mode.upper()
    badge_box = draw.textbbox((0, 0), badge_text, font=meta_font)
    badge_width = badge_box[2] - badge_box[0] + 28
    badge_x = width - left - badge_width
    draw.rounded_rectangle(
        (badge_x, 48, badge_x + badge_width, 80),
        radius=16,
        fill=(209, 222, 220),
    )
    draw.text(
        (badge_x + 14, 55),
        badge_text,
        font=meta_font,
        fill=(42, 68, 68),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(args.output, quality=94, subsampling=1)


if __name__ == "__main__":
    main()
