#!/usr/bin/env python3
"""Reusable Olise-inspired CRT / camcorder post-processing core."""

from pathlib import Path
import math
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parent
CLASSIFIER = ROOT / "classify_scene.swift"
MOTION_LEVELS = ("static", "mild", "sports")


def clip(a):
    return np.clip(a, 0.0, 1.0)


def luma(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def bilinear_sample(a, sx, sy):
    h, w = a.shape[:2]
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1)
    x0 = np.clip(x0, 0, w - 1)
    y0 = np.clip(y0, 0, h - 1)
    fx = (sx - x0)[..., None]
    fy = (sy - y0)[..., None]
    top = a[y0, x0] * (1.0 - fx) + a[y0, x1] * fx
    bottom = a[y1, x0] * (1.0 - fx) + a[y1, x1] * fx
    return top * (1.0 - fy) + bottom * fy


def mild_fisheye(a, strength=0.010):
    """Subtle screen bulge on every image, progressively stronger at edges."""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xx - (w - 1) / 2) / max((w - 1) / 2, 1)
    ny = (yy - (h - 1) / 2) / max((h - 1) / 2, 1)
    r2 = nx * nx + ny * ny
    factor = 1.0 + strength * r2
    warped_x = nx * factor
    warped_y = ny * factor
    sx = (warped_x + 1.0) * (w - 1) / 2
    sy = (warped_y + 1.0) * (h - 1) / 2
    sampled = bilinear_sample(a, sx, sy)

    # Clamped sampling creates barcode-like stretched borders. Fade the virtual
    # screen as the warped coordinates approach or leave its valid face.
    screen_edge = np.maximum(np.abs(warped_x), np.abs(warped_y))
    screen_mask = 1.0 - _smoothstep(0.982, 1.024, screen_edge)
    return sampled * (0.72 + 0.28 * screen_mask[..., None])


def pixelate_and_blur(image, motion_level="static"):
    """CRT softness without using whole-frame blur as the motion effect."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    w, h = image.size
    short_edge = min(w, h)
    low = image.resize(
        (max(1, w // 2), max(1, h // 2)),
        Image.Resampling.BOX,
    )
    pixelated = low.resize((w, h), Image.Resampling.NEAREST)
    motion_index = {
        "static": 0,
        "mild": 1,
        "sports": 2,
    }[motion_level]
    if short_edge < 480:
        # Phone-video reposts have already been resized and compressed once.
        # Keep the CRT softness, but retain UI type and the subject silhouette.
        pixel_mix = (0.24, 0.28, 0.33)[motion_index]
        blur_radius = (0.26, 0.30, 0.35)[motion_index]
    elif short_edge < 720:
        pixel_mix = (0.45, 0.49, 0.54)[motion_index]
        blur_radius = (0.45, 0.50, 0.56)[motion_index]
    else:
        pixel_mix = (0.58, 0.62, 0.66)[motion_index]
        blur_radius = (0.55, 0.58, 0.62)[motion_index]
    pixelated = Image.blend(image, pixelated, pixel_mix)
    return pixelated.filter(ImageFilter.GaussianBlur(radius=blur_radius))


def _smoothstep(edge0, edge1, value):
    t = clip((value - edge0) / max(edge1 - edge0, 1e-5))
    return t * t * (3.0 - 2.0 * t)


def _hue_window(hue, center, half_width, feather):
    distance = np.abs(hue - center)
    distance = np.minimum(distance, 1.0 - distance)
    return 1.0 - _smoothstep(
        half_width - feather,
        half_width,
        distance,
    )


def _hue_and_saturation(a):
    high = a.max(axis=2)
    low = a.min(axis=2)
    delta = high - low
    safe = np.maximum(delta, 1e-6)
    hue = np.zeros_like(high)
    red_high = a[..., 0] >= np.maximum(a[..., 1], a[..., 2])
    green_high = (a[..., 1] > a[..., 0]) & (a[..., 1] >= a[..., 2])
    blue_high = ~(red_high | green_high)
    hue[red_high] = (
        (a[..., 1][red_high] - a[..., 2][red_high]) / safe[red_high]
    ) % 6.0
    hue[green_high] = (
        (a[..., 2][green_high] - a[..., 0][green_high]) / safe[green_high]
    ) + 2.0
    hue[blue_high] = (
        (a[..., 0][blue_high] - a[..., 1][blue_high]) / safe[blue_high]
    ) + 4.0
    hue /= 6.0
    saturation = delta / np.maximum(high, 1e-5)
    return hue, saturation


def adaptive_white_balance(image):
    """Partially neutralize source lighting before applying the CRT style cast."""
    source = ImageOps.exif_transpose(image).convert("RGB")
    a = np.asarray(source, np.float32) / 255.0
    _, saturation = _hue_and_saturation(a)
    y = luma(a)

    # Prefer mid/high neutral surfaces such as shirts, walls, seats, and signage.
    neutral_mask = (
        (saturation < 0.20)
        & (y > 0.22)
        & (y < 0.90)
    )
    if neutral_mask.mean() < 0.012:
        neutral_mask = (
            (saturation < 0.30)
            & (y > 0.18)
            & (y < 0.92)
        )
    if neutral_mask.any():
        neutral = np.median(a[neutral_mask], axis=0)
    else:
        usable = (y > 0.15) & (y < 0.88)
        neutral = np.median(a[usable], axis=0) if usable.any() else a.mean((0, 1))

    target = float(np.exp(np.mean(np.log(np.maximum(neutral, 1e-4)))))
    neutral_gains = np.power(
        np.clip(target / np.maximum(neutral, 1e-4), 0.76, 1.28),
        0.72,
    )

    # A warm scene may contain no truly low-saturation white. Estimate the
    # illuminant again from the brightest plausible surfaces (white fur,
    # clothing, seats, walls), then trust it only when warm contamination is clear.
    bright_floor = np.percentile(y, 82)
    bright_mask = (
        (y > bright_floor)
        & (y < 0.97)
        & (saturation < 0.62)
    )
    if bright_mask.any():
        white = np.percentile(a[bright_mask], 70, axis=0)
        white_target = float(
            np.exp(np.mean(np.log(np.maximum(white, 1e-4))))
        )
        white_gains = np.power(
            np.clip(white_target / np.maximum(white, 1e-4), 0.70, 1.50),
            0.88,
        )
        warm_ratio = float(white[0] / max(white[2], 1e-4))
        warm_mix = float(0.28 + 0.62 * _smoothstep(1.12, 1.75, warm_ratio))
        gains = np.exp(
            np.log(np.maximum(neutral_gains, 1e-5)) * (1.0 - warm_mix)
            + np.log(np.maximum(white_gains, 1e-5)) * warm_mix
        )
    else:
        gains = neutral_gains

    a *= gains[None, None, :]
    return Image.fromarray(np.uint8(clip(a) * 255))


def lift_saturation_and_teal(a):
    """Collapse warm/green families first, then compensate surviving CRT color."""
    hue, saturation = _hue_and_saturation(a)
    source_luma = luma(a)
    red = (
        _hue_window(hue, 0.985, 0.072, 0.032)
        * _smoothstep(0.30, 0.64, saturation)
    )[..., None]
    green = (
        _hue_window(hue, 0.305, 0.150, 0.065)
        * _smoothstep(0.14, 0.48, saturation)
    )[..., None]
    yellow = (
        _hue_window(hue, 0.145, 0.090, 0.045)
        * _smoothstep(0.28, 0.62, saturation)
    )[..., None]
    cool = (
        _hue_window(hue, 0.565, 0.175, 0.075)
        * _smoothstep(0.16, 0.52, saturation)
    )[..., None]
    violet = (
        _hue_window(hue, 0.865, 0.125, 0.055)
        * _smoothstep(0.08, 0.34, saturation)
    )[..., None]
    # Warm skin and indoor tungsten surfaces still need to feel cool, but they
    # must not cross the red/blue axis into synthetic purple.
    warm_family = (
        _hue_window(hue, 0.060, 0.105, 0.050)
        * _smoothstep(0.07, 0.34, saturation)
        * (1.0 - _smoothstep(0.84, 0.98, source_luma))
    )[..., None]

    # What the references make most visible: red gains density and darkness,
    # while clean green loses chroma and becomes a grey-green residue.
    y = luma(a)[..., None]
    dark_red = y * np.array([0.92, 0.53, 0.45], np.float32)
    a = a * (1.0 - red * 0.50) + dark_red * red * 0.50
    a *= 1.0 - red * 0.24

    y = luma(a)[..., None]
    grey_green = y * np.array([0.91, 0.985, 1.005], np.float32)
    a = a * (1.0 - green * 0.70) + grey_green * green * 0.70
    a *= 1.0 - green * 0.06

    y = luma(a)[..., None]
    dirty_yellow = y * np.array([1.00, 0.91, 0.82], np.float32)
    a = a * (1.0 - yellow * 0.34) + dirty_yellow * yellow * 0.34
    a *= 1.0 - yellow * 0.10

    # Phone LEDs and livestream beauty lighting often contain violet patches.
    # The reference palette resolves those toward muted blue-cyan, not purple.
    y = luma(a)[..., None]
    grey_cyan = y * np.array([0.94, 1.000, 1.018], np.float32)
    a = a * (1.0 - violet * 0.72) + grey_cyan * violet * 0.72

    # Cyan/blue remain the surviving color family before global compensation.
    y = luma(a)[..., None]
    a = y + (a - y) * (1.0 + cool * 0.16)

    # CRT exposure compensation is moderate, not a return to modern brightness.
    y = luma(a)
    p05, p50, p95 = np.percentile(y, (5, 50, 95))
    mapped = np.interp(
        y,
        (0.0, p05, p50, p95, 1.0),
        (
            0.014,
            0.060,
            0.355,
            0.745,
            0.91,
        ),
    )
    a *= (mapped / np.maximum(y, 0.018))[..., None]

    y = luma(a)
    shadow = np.power(1.0 - y, 1.55)[..., None]
    mid = np.clip(1.0 - np.abs(y - 0.44) * 2.25, 0.0, 1.0)[..., None]
    high = np.power(y, 2.1)[..., None]
    cast = (
        shadow * np.array([-0.032, 0.017, 0.058], np.float32)
        + mid * np.array([-0.030, 0.014, 0.048], np.float32)
        + high * np.array([-0.020, 0.008, 0.027], np.float32)
    )
    # Reduce only the blue-heavy component on warm-family pixels. The green
    # component stays, so protected skin remains inside the cold-cyan world.
    cast[..., 0] *= 1.0 - warm_family[..., 0] * 0.32
    cast[..., 1] += warm_family[..., 0] * 0.010
    cast[..., 2] *= 1.0 - warm_family[..., 0] * 0.62
    a += cast
    a[..., 0] *= 0.905 + warm_family[..., 0] * 0.035
    a[..., 1] *= 1.025 + warm_family[..., 0] * 0.010
    a[..., 2] *= 1.115 - warm_family[..., 0] * 0.070

    y = luma(a)[..., None]
    # "Increase saturation" now boosts the surviving cyan/blue hierarchy,
    # rather than restoring every original hue equally.
    return clip(y + (a - y) * 1.075)


def dual_scan_screen(a, motion_level="static"):
    """CRT RGB grille, scanlines, and scene-scaled field instability."""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # A filmed screen is never perfectly synchronized. Sports gets a stronger
    # rolling field slip instead of a longer synthetic motion blur.
    if motion_level == "sports":
        band = np.exp(
            -0.5 * ((yy - h * 0.53) / max(h * 0.12, 1.0)) ** 2
        )
        field_shift = 0.65 * np.sin(yy / 7.5) + band * 2.40
        a = bilinear_sample(a, xx + field_shift, yy)
        # Odd/even fields capture motion at slightly different instants.
        # Blend alternating two-line groups to form restrained broadcast combing.
        delayed_field = bilinear_sample(a, xx + max(1.4, w / 620.0), yy)
        field_rows = ((yy.astype(np.int32) // 2) % 2).astype(np.float32)
        field_mix = (field_rows * 0.32)[..., None]
        a = a * (1.0 - field_mix) + delayed_field * field_mix
    elif motion_level == "mild":
        field_shift = 0.25 * np.sin(yy / 9.0)
        a = bilinear_sample(a, xx + field_shift, yy)

    # Consumer CRT chroma registration: luma remains legible while red and
    # blue resolve on slightly different columns.
    register_px = max(0.55, min(1.35, w / 1050.0))
    registered = a.copy()
    registered[..., 0] = bilinear_sample(
        a, xx - register_px, yy
    )[..., 0]
    registered[..., 2] = bilinear_sample(
        a, xx + register_px, yy
    )[..., 2]
    register_mix = {
        "static": 0.38,
        "mild": 0.47,
        "sports": 0.56,
    }[motion_level]
    a = a * (1.0 - register_mix) + registered * register_mix

    scan_pitch = max(4.2, w / 250.0)
    horizontal = np.sin(
        2 * math.pi * (yy / scan_pitch + 0.025 * np.sin(xx / 151.0))
    )
    triad_pitch = max(2.8, w / 330.0)
    phase = 2 * math.pi * (
        xx / triad_pitch
        + 0.040 * np.sin(yy / 91.0)
        + 0.020 * np.sin((xx + yy) / 173.0)
    )
    triad_strength = {
        "static": 0.085,
        "mild": 0.105,
        "sports": 0.130,
    }[motion_level]
    phosphor = np.empty_like(a)
    phosphor[..., 0] = 1.0 + triad_strength * np.cos(phase)
    phosphor[..., 1] = 1.0 + triad_strength * np.cos(
        phase - 2 * math.pi / 3
    )
    phosphor[..., 2] = 1.0 + triad_strength * np.cos(
        phase - 4 * math.pi / 3
    )
    vertical_grille = np.sin(phase) * 0.034
    diagonal = np.sin(2 * math.pi * (xx / 181.0 - yy / 239.0))
    a *= phosphor
    a *= (
        1.0
        + horizontal[..., None] * 0.018
        + vertical_grille[..., None]
        + diagonal[..., None] * 0.015
    )
    return clip(a)


def dream_signal(a, strength=0.55):
    """Low-frequency CRT aura and signal drift without a purple wash."""
    strength = float(np.clip(strength, 0.0, 1.5))
    if strength <= 0.0:
        return a

    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    y = luma(a)

    # Let color resolve slightly more slowly than luma, like consumer CRT
    # chroma bandwidth rather than ordinary Gaussian defocus.
    color_layer = Image.fromarray(np.uint8(clip(a) * 255)).filter(
        ImageFilter.GaussianBlur(radius=max(0.8, min(w, h) * 0.0018))
    )
    color_layer = np.asarray(color_layer, np.float32) / 255.0
    chroma_bleed = np.clip(0.18 * strength, 0.0, 0.26)
    y_base = y[..., None]
    soft_y = luma(color_layer)[..., None]
    a = (
        y_base
        + (a - y_base) * (1.0 - chroma_bleed)
        + (color_layer - soft_y) * chroma_bleed
    )

    # A broad cyan-white phosphor aura around luminous screen content.
    bright = _smoothstep(0.48, 0.88, y)[..., None]
    glow_source = clip(a) * bright
    aura = Image.fromarray(np.uint8(glow_source * 255)).filter(
        ImageFilter.GaussianBlur(radius=max(3.0, min(w, h) * 0.024))
    )
    aura = np.asarray(aura, np.float32) / 255.0
    aura *= np.array([0.74, 1.00, 1.10], np.float32)
    aura_mix = 0.240 * strength
    a = 1.0 - (1.0 - clip(a)) * (1.0 - clip(aura) * aura_mix)

    # Large, slowly varying chroma clouds read as unstable CRT memory rather
    # than a flat teal overlay. Keep them strongest in shadows and mids.
    cloud_a = np.sin(xx / 121.0 + yy / 173.0 + 0.7)
    cloud_b = np.sin(xx / 263.0 - yy / 149.0 + 1.9)
    cloud = (cloud_a * 0.62 + cloud_b * 0.38)[..., None]
    shadow = np.power(1.0 - y, 1.65)[..., None]
    mid = np.clip(1.0 - np.abs(y - 0.43) * 2.35, 0.0, 1.0)[..., None]
    a += (
        cloud
        * (
            shadow * np.array([-0.005, 0.006, 0.012], np.float32)
            + mid * np.array([-0.008, 0.008, 0.016], np.float32)
        )
        * strength
    )

    # A broad rolling exposure band and diagonal interference make the screen
    # feel captured at an instant, not generated as a perfectly flat overlay.
    band_center = h * (0.42 + 0.07 * math.sin(w * 0.013))
    band = np.exp(
        -0.5 * ((yy - band_center) / max(h * 0.16, 1.0)) ** 2
    )
    band -= band.mean()
    interference = np.sin(2 * math.pi * (xx / 197.0 - yy / 257.0 + 0.23))
    a *= (
        1.0
        + band[..., None] * (0.026 * strength)
        + interference[..., None] * (0.0070 * strength)
    )

    # Deterministic fine luma grain: enough to break digital cleanliness,
    # never enough to read as modern film-grain software.
    seed = int((w * 73856093) ^ (h * 19349663)) & 0xFFFFFFFF
    grain = np.random.default_rng(seed).normal(
        0.0,
        0.0060 * strength,
        (h, w, 1),
    ).astype(np.float32)
    return clip(a + grain)


def phosphor_persistence(a, motion_level, intensity=1.0):
    """Scaled-down continuous shutter persistence, not discrete copied ghosts."""
    if motion_level == "static":
        return a
    intensity = float(np.clip(intensity, 0.0, 2.0))

    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    y = luma(a)
    gx = np.zeros_like(y)
    gy = np.zeros_like(y)
    gx[:, 1:] = np.abs(y[:, 1:] - y[:, :-1])
    gy[1:, :] = np.abs(y[1:, :] - y[:-1, :])
    edge = _smoothstep(0.012, 0.105, np.sqrt(gx * gx + gy * gy))
    bright = _smoothstep(0.56, 0.90, y)

    if motion_level == "mild":
        max_x_ratio, max_y_ratio = 0.004, 0.0008
        trail_mix, samples = 0.050, 7
    else:
        max_x_ratio, max_y_ratio = 0.010, 0.0020
        trail_mix, samples = 0.100, 9

    max_dx = w * max_x_ratio * intensity
    max_dy = h * max_y_ratio * intensity
    trail = np.zeros_like(a)
    total_weight = 0.0
    for index in range(samples):
        t = index / max(samples - 1, 1)
        weight = math.exp(-2.55 * t)
        trail += bilinear_sample(a, xx + max_dx * t, yy + max_dy * t) * weight
        total_weight += weight
    trail /= max(total_weight, 1e-6)

    # Keep the underlying frame dominant. Edges and bright phosphors carry a
    # little more persistence, as they would on a filmed CRT.
    profile = 0.58 + edge * 0.34 + bright * 0.10
    mask = clip(trail_mix * intensity * profile)[..., None]
    return clip(a * (1.0 - mask) + trail * mask)


def black_edge_and_glow(a):
    """Soft CRT border plus exposure-adaptive highlight bloom."""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = np.abs((xx - (w - 1) / 2) / max((w - 1) / 2, 1))
    ny = np.abs((yy - (h - 1) / 2) / max((h - 1) / 2, 1))
    edge = np.maximum(nx, ny)
    border = 1.0 - 0.08 * clip((edge - 0.89) / 0.11) ** 1.7
    a *= border[..., None]

    median = float(np.median(luma(a)))
    glow_strength = float(np.clip(0.19 - median * 0.20, 0.055, 0.145))
    threshold = 0.54 if median < 0.34 else 0.64
    bright = clip((luma(a) - threshold) / max(1.0 - threshold, 0.01))[..., None]
    highlights = clip(a) * bright
    bloom = Image.fromarray(np.uint8(highlights * 255)).filter(
        ImageFilter.GaussianBlur(radius=max(4, min(w, h) * 0.010))
    )
    bloom = np.asarray(bloom, np.float32) / 255.0
    return clip(1.0 - (1.0 - clip(a)) * (1.0 - bloom * glow_strength))


def render(
    image,
    motion_level="static",
    motion_strength=1.0,
    dream_strength=0.55,
):
    """Render one PIL image while preserving its dimensions and aspect ratio."""
    if motion_level not in MOTION_LEVELS:
        raise ValueError(f"Unknown motion level: {motion_level}")
    normalized = adaptive_white_balance(image)
    softened = pixelate_and_blur(normalized, motion_level)
    a = np.asarray(softened, np.float32) / 255.0
    a = lift_saturation_and_teal(a)
    a = phosphor_persistence(a, motion_level, intensity=motion_strength)
    a = dual_scan_screen(a, motion_level)
    a = dream_signal(a, strength=dream_strength)
    strength = {
        "static": 0.008,
        "mild": 0.012,
        "sports": 0.018,
    }[motion_level]
    a = mild_fisheye(a, strength=strength)
    return black_edge_and_glow(a)


def _fallback_scene(path):
    return {
        "path": str(path),
        "level": "static",
        "sport": 0.0,
        "faces": 0,
        "largest_face": 0.0,
        "classifier": "fallback",
    }


def classify_paths(paths):
    """Classify motion scale with macOS Vision; safely default to static."""
    paths = [Path(path).resolve() for path in paths]
    if not paths:
        return []
    if shutil.which("swift") is None or not CLASSIFIER.exists():
        return [_fallback_scene(path) for path in paths]

    try:
        process = subprocess.run(
            ["swift", str(CLASSIFIER), *(str(path) for path in paths)],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except (OSError, subprocess.SubprocessError):
        return [_fallback_scene(path) for path in paths]

    parsed = []
    for path, line in zip(paths, process.stdout.splitlines()):
        labels = {}
        faces = 0
        largest_face = 0.0
        for field in line.split("\t")[1:]:
            if field.startswith("faces="):
                faces = int(field.split("=", 1)[1])
            elif field.startswith("largest_face="):
                largest_face = float(field.split("=", 1)[1])
            elif field.startswith("labels="):
                for item in field.split("=", 1)[1].split(","):
                    if ":" in item:
                        name, confidence = item.rsplit(":", 1)
                        labels[name] = float(confidence)

        sport_score = max(
            (
                labels.get(name, 0.0)
                for name in ("sport", "soccer", "basketball", "ballgames", "recreation")
            ),
            default=0.0,
        )
        people_score = max(labels.get("people", 0.0), labels.get("adult", 0.0))
        if sport_score >= 0.72 and largest_face < 0.018:
            level = "sports"
        elif sport_score >= 0.28:
            level = "mild"
        elif faces > 0 or people_score >= 0.45:
            level = "static"
        else:
            level = "static"
        parsed.append(
            {
                "path": str(path),
                "level": level,
                "sport": sport_score,
                "faces": faces,
                "largest_face": largest_face,
                "classifier": "vision",
            }
        )

    while len(parsed) < len(paths):
        parsed.append(_fallback_scene(paths[len(parsed)]))
    return parsed
