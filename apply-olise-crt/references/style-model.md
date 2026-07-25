# Style model

## Visual stack

The look is a simulation of a camcorder or camera filming an old CRT, not a LUT alone:

1. Adaptive source white balance
2. Resolution- and scene-aware 2× pixel softness
3. Restrained Gaussian blur that removes digital sharpness
4. Two perpendicular scan-screen layers
5. Selective hue-family remapping
6. Cold cyan-blue CRT cast
7. Short continuous phosphor persistence for moving scenes
8. Cyan-white aura, low-frequency signal drift, rolling exposure, and fine CRT noise
9. Scene-scaled edge fisheye
10. Soft black CRT border and exposure-aware glow

Do not crop, recompose, synthesize subjects, or impose a 4:3 crop inside the renderer.

## Scene adaptation

| Scene | Typical examples | Fisheye | Phosphor persistence |
|---|---|---:|---|
| Static | portrait, group photo, mirror selfie, screenshot, still life | 0.008 | none |
| Mild | walking, gesture, candid performance | 0.012 | up to 0.4% frame width, 5% mix |
| Sports | kick, jump, sprint, airborne action | 0.018 | up to 1.0% frame width, 10% mix |

The macOS Vision classifier is conservative. Override a visibly walking image to `mild`; reserve `sports` for clear athletic action.

## Resolution adaptation

Fixed pixelation destroys reposted or screenshot imagery, so softness scales with the short edge:

| Short edge | Static pixel blend / blur | Mild pixel blend / blur | Sports pixel blend / blur |
|---:|---:|---:|---:|
| under 480 px | 24% / 0.26 | 28% / 0.30 | 33% / 0.35 |
| 480–719 px | 45% / 0.45 | 49% / 0.50 | 54% / 0.56 |
| 720 px or more | 58% / 0.55 | 62% / 0.58 | 66% / 0.62 |

## Color behavior

- **Red:** increase density and darkness; retain muted red identity.
- **Green:** strongly collapse chroma toward grey-green.
- **Yellow:** reduce brightness and cleanliness; bias toward dirty ochre.
- **Cyan/blue:** preserve and slightly reinforce as the dominant surviving family.
- **Violet/magenta:** collapse toward cool grey so LED light and beauty filters do not produce purple facial patches.
- **Skin/warm neutrals:** reduce the blue-heavy component locally while retaining the green/cyan environmental cast.

Run adaptive white balance before the style mapping. This is essential for tungsten interiors and warm phone photos; a fixed cyan overlay is not equivalent.

## CRT texture

- Use a coarse horizontal scan layer plus a lower-scale stretched vertical layer.
- Make the vertical RGB phosphor grille more visible than the horizontal scanline.
- Increase RGB registration error and rolling field slip for sports instead of adding long blur.
- Blend slightly delayed odd/even fields in sports to create restrained broadcast combing.
- Keep 2× pixel softness visible, but use less than 1 px of Gaussian blur at normal resolution.
- Generate motion from a dense, exponentially weighted shutter trail. Keep the main frame dominant and avoid readable duplicate ghosts.
- Make glow exposure-aware so bright sources do not bloom uncontrollably.
- Apply the border and fisheye harmoniously across all scenes.
- Fade warped samples into the CRT edge; never clamp them into stretched barcode bands.

## Dream signal

- Keep the default dream strength moderate (`0.55`).
- Add a broad cyan-white aura only around bright phosphors.
- Use low-frequency chroma clouds in shadows and mids instead of a flat color overlay.
- Add one broad rolling exposure band, faint diagonal interference, and deterministic fine luma noise.
- Never introduce a generic pink or violet dreamcore grade; it conflicts with the reference palette and skin protection.

## Failure modes

- **Everything becomes uniformly blue:** selective hue separation has been lost.
- **Skin turns purple:** magenta survived or the blue cast is too global.
- **Static portrait looks melted:** blur/pixelation or motion treatment is too strong.
- **Grass stays neon green:** green-family collapse is too weak.
- **Red signage stays bright:** red density/darkening is too weak.
- **UI text disappears:** use the low-resolution softness branch.
