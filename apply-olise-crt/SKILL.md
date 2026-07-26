---
name: apply-olise-crt
description: Apply a scene-adaptive cold-cyan CRT, VHS, old-TV, or camcorder look to one or more raster photos. Use when a user asks to “套奥利塞效果”, reproduce the Olise photo vibe, add CRT scanlines or screen re-photography texture, batch-style JPG/PNG images, or tune the effect differently for portraits, screenshots, still lifes, walking scenes, and sports action.
---

# Apply Olise CRT

Apply the bundled deterministic renderer. Preserve the source dimensions and composition; change only color, screen texture, softness, glow, border, and scene-scaled fisheye.

## Run the effect

1. Resolve every input to an absolute path.
2. Choose `auto` unless the image visibly contradicts the classifier:
   - Use `static` for portraits, group photos, screenshots, interiors, objects, and posed scenes.
   - Use `mild` for walking, gesturing, casual performance, or a lightly dynamic candid.
   - Use `sports` only for unmistakable high-energy athletic action.
3. Run:

```bash
python3 scripts/apply_olise_crt.py INPUT... -o OUTPUT_DIR --motion auto
```

Override the scene scale when needed:

```bash
python3 scripts/apply_olise_crt.py INPUT -o OUTPUT_DIR --motion mild
```

Tune only the short CRT persistence without changing the color model:

```bash
python3 scripts/apply_olise_crt.py INPUT -o OUTPUT_DIR --motion sports --motion-strength 1.25
```

Tune the dreamlike screen aura independently:

```bash
python3 scripts/apply_olise_crt.py INPUT -o OUTPUT_DIR --dream-strength 0.70
```

The runtime requires NumPy and Pillow. If unavailable, install from `scripts/requirements.txt` or use the host application's bundled Python environment.

## Inspect before delivery

Open every result and check:

- Red becomes darker and denser, not merely grey.
- Green loses saturation into grey-green.
- Yellow becomes dirtier and less luminous.
- Cyan and blue remain the surviving color family.
- Skin stays inside the cold environment without becoming purple or green.
- Small screenshots retain readable UI and recognizable silhouettes.
- Static scenes do not receive sports-scale distortion or phosphor persistence.
- Moving scenes stay readable; a short continuous CRT lag is weighted toward high-contrast and bright edges.
- Scanlines, blur, glow, and fisheye read as one CRT surface rather than separate gimmicks.
- Dream haze stays cyan-white and low-frequency; it must not become a flat purple wash.

If classification is wrong, rerun with an explicit motion level. Keep the bundled persistence short and continuous; do not turn it into several readable duplicate subjects unless the user separately requests that stronger treatment.

## Tune or explain the model

Read [references/style-model.md](references/style-model.md) before changing color families, scene thresholds, blur scaling, or fisheye strengths. Keep adjustments selective; avoid solving one source image by applying a global cast that damages the other scene types.
