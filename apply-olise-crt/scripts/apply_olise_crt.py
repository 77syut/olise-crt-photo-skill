#!/usr/bin/env python3
"""Single-command and batch entry point for the V7 CRT effect."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from olise_crt_core import MOTION_LEVELS, classify_paths, render


def parse_args():
    parser = argparse.ArgumentParser(
        description="Apply the Olise-inspired CRT / camcorder effect."
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path.cwd() / "olise-crt-output",
    )
    parser.add_argument(
        "--motion",
        choices=("auto", *MOTION_LEVELS),
        default="auto",
        help="Auto uses macOS Vision; explicit levels override recognition.",
    )
    parser.add_argument("--quality", type=int, default=94)
    parser.add_argument(
        "--motion-strength",
        type=float,
        default=1.0,
        help="Scale short CRT persistence from 0.0 to 2.0.",
    )
    parser.add_argument(
        "--dream-strength",
        type=float,
        default=0.55,
        help="Scale cyan phosphor aura and CRT signal drift from 0.0 to 1.5.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    inputs = [path.expanduser().resolve() for path in args.inputs]
    missing = [path for path in inputs if not path.is_file()]
    if missing:
        raise SystemExit("Missing input: " + ", ".join(str(path) for path in missing))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.motion == "auto":
        scenes = classify_paths(inputs)
    else:
        scenes = [
            {
                "path": str(path),
                "level": args.motion,
                "classifier": "override",
                "sport": 0.0,
                "faces": 0,
                "largest_face": 0.0,
            }
            for path in inputs
        ]

    for path, scene in zip(inputs, scenes):
        with Image.open(path) as image:
            source = ImageOps.exif_transpose(image).convert("RGB")
            original_size = source.size
            result = Image.fromarray(
                np.uint8(
                    render(
                        source,
                        scene["level"],
                        motion_strength=max(0.0, min(2.0, args.motion_strength)),
                        dream_strength=max(0.0, min(1.5, args.dream_strength)),
                    )
                    * 255
                )
            )
        if result.size != original_size:
            raise RuntimeError(f"Size changed unexpectedly: {path}")
        output = args.output_dir / f"{path.stem}-olise-crt.jpg"
        result.save(
            output,
            quality=max(1, min(100, args.quality)),
            subsampling=1,
        )
        print(
            f"{output}\tmotion={scene['level']}"
            f"\tclassifier={scene['classifier']}"
        )


if __name__ == "__main__":
    main()
