# Style model

## Visual stack

The look is a simulation of a camcorder or camera filming an old CRT, not a LUT alone:

1. Adaptive source white balance
2. Resolution-aware 2× pixel softness
3. Gaussian blur that removes digital sharpness
4. Two perpendicular scan-screen layers
5. Selective hue-family remapping
6. Cold cyan-blue CRT cast
7. Scene-scaled edge fisheye
8. Soft black CRT border and exposure-aware glow

Do not crop, recompose, synthesize subjects, or impose a 4:3 crop inside the renderer.

## Scene adaptation

| Scene | Typical examples | Fisheye | Motion trail |
|---|---|---:|---|
| Static | portrait, group photo, mirror selfie, screenshot, still life | 0.010 | none |
| Mild | walking, gesture, candid performance | 0.016 | none |
| Sports | kick, jump, sprint, airborne action | 0.022 | none |

The macOS Vision classifier is conservative. Override a visibly walking image to `mild`; reserve `sports` for clear athletic action.

## Resolution adaptation

Fixed pixelation destroys reposted or screenshot imagery, so softness scales with the short edge:

| Short edge | Pixelated blend | Gaussian radius |
|---:|---:|---:|
| under 480 px | 46% | 0.58 |
| 480–719 px | 74% | 0.92 |
| 720 px or more | 100% | 1.25 |

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
- Keep pixelation near 2× and blur near 1–2 px at normal resolution.
- Make glow exposure-aware so bright sources do not bloom uncontrollably.
- Apply the border and fisheye harmoniously across all scenes.

## Failure modes

- **Everything becomes uniformly blue:** selective hue separation has been lost.
- **Skin turns purple:** magenta survived or the blue cast is too global.
- **Static portrait looks melted:** blur/pixelation or motion treatment is too strong.
- **Grass stays neon green:** green-family collapse is too weak.
- **Red signage stays bright:** red density/darkening is too weak.
- **UI text disappears:** use the low-resolution softness branch.

