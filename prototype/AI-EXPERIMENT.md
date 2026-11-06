# AI visual wall annotation side experiment

The user requested a best-effort AI guess for the three local maps, up to four visual revision rounds, favoring the fewest useful wall segments. This is a separate exploration and does not replace the Auto-Wall-parity milestone.

## Result

The private local comparison page now includes `AI visual guess · 4 passes`:

| Map | Round 1 | Round 2 | Round 3 | Selected round 4 |
| --- | ---: | ---: | ---: | ---: |
| Building | 4 | 4 | 4 | 4 |
| Tavern | 11 | 14 | 13 | 13 |
| Caverns | 597 | 168 | 196 | 186 |

- First pass: visual cabin/tavern structural outlines; visually chosen near-black cavern void tracing assisted by image geometry tools.
- Second pass: corrected tavern open arch/stair passages and missing partition; removed cavern small shadow shapes and excess detail.
- Third pass: hand-edited explicit cavern wall chains/regions, added significant structural masses, corrected the middle island boundary, and merged a collinear tavern boundary.
- Fourth pass: removed unnecessary cavern bends with bounded geometric simplification, inspected the final overlays, and checked image-selected blocked/open sight lines. Kept the fourth version as the best trade-off, not necessarily the mathematically smallest geometry.

Selected spot checks: building 4/4, tavern 9/9, cavern 10/10. These checks were chosen by the same AI making the annotations; they are illustrative consistency checks, not independent accuracy validation. Closed doors/windows are treated as barriers, obvious open arches stay open, and small furniture/rock detail is omitted. Determining which cavern cliffs are full-height opaque walls remains subjective without author input. This experiment produces walls only, not movable portals or lights.

## What this establishes

It is a one-off AI-assisted visual/coordinate annotation with geometry tooling, not a fully autonomous image-to-JSON service. The final wall coordinates were constructed without reading the supplied UVTT wall arrays. Earlier conversation included some reference overlays, so this is not a blinded benchmark. It does not measure model API cost, inference latency, robustness on held-out maps, or automated reproducibility.

## Local assets and rebuild

Private source images, per-round coordinates/overlays, final UVTT wall data, and review checks remain under `/private/tmp/auto-wall-ai/`. They are not committed or uploaded. User-map image and geometry data also remain in the local review page; do not publish it without permission.

`python3 prototype/add_ai_review.py` reads the private `round4.json` annotations, checks coordinate bounds/duplicates/zero-length segments, scales them back to original pixels, exports no-image UVTT wall documents locally, and attaches the candidate to `/private/tmp/auto-wall-detection-review/review.html`. The page can toggle detected/reference geometry and the AI-selected visibility checks. The rebuild script is captured here; the private annotations are deliberately not bundled with it.
