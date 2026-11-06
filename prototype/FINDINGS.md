# Initial detection experiment findings

No candidate meets the intended three-style quality gate. These are exploratory measurements on Apple M4, macOS-27.0-arm64-arm-64bit-Mach-O. Longest working dimension 1600 px; three fresh processes per candidate, warm filesystem cache; no p95/concurrency claim.

| Map | Candidate | Wall segments | Detection median ms | Peak process RSS MiB | Reference length agreement | Reference coverage | Visibility disagreements / 100 | Light matches / candidates / reference |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Building | dark40 | 3056 | 59.8 | 191.2 | 1.7% | 55.1% | 40 | 5 / 48 / 7 |
| Building | dark70 | 2687 | 60.1 | 191.3 | 6.2% | 90.3% | 21 | 5 / 48 / 7 |
| Building | edges | 705 | 129.6 | 201.4 | 17.5% | 90.3% | 12 | 5 / 48 / 7 |
| Building | void | 474 | 100.8 | 191.9 | 0.0% | 0.0% | 25 | 5 / 48 / 7 |
| Tavern | dark40 | 5748 | 61.9 | 160.0 | 19.5% | 93.4% | 56 | 2 / 19 / 41 |
| Tavern | dark70 | 3809 | 62.1 | 159.2 | 18.5% | 72.0% | 48 | 2 / 19 / 41 |
| Tavern | edges | 2964 | 118.5 | 168.5 | 38.6% | 93.8% | 48 | 2 / 19 / 41 |
| Tavern | void | 5 | 63.4 | 158.2 | 81.8% | 41.1% | 13 | 2 / 19 / 41 |
| Caverns | dark40 | 8871 | 78.8 | 228.8 | 38.1% | 74.3% | 27 | 18 / 47 / 21 |
| Caverns | dark70 | 6166 | 75.1 | 230.0 | 28.9% | 33.0% | 44 | 18 / 47 / 21 |
| Caverns | edges | 10883 | 156.9 | 242.2 | 53.7% | 86.9% | 31 | 18 / 47 / 21 |
| Caverns | void | 1717 | 107.7 | 227.1 | 38.4% | 45.1% | 29 | 18 / 47 / 21 |

## Interpretation

- Dark-region and edge contours over-detect texture, furniture, trees, image borders, and duplicate sides of thick walls. A fast raw contour tracer is not enough.
- The near-black-region candidate reduces cavern segment count, but does not establish usable topology. It misses most tavern walls. One fixed mask is not a convincing universal default.
- Warm-color candidates detect some reference lights but many non-light regions; reference lights themselves need visual review. This heuristic does not satisfy conservative detection yet.
- Controlled blank cases return no walls or lights; the simple closed room produces eight segments for threshold methods (two sides of thick walls), and the warm point is detected while white clutter is rejected. These sanity cases are much easier than actual maps.
- Reference agreement and random visibility disagreements are diagnostics, not ground-truth precision/recall. No human-reviewed annotation, frozen quality gate, Linux benchmark, concurrent load test, or automatic-door experiment has been completed.

## Next human decision

Review local overlays before freezing numeric gates. Recommended next experiment: evaluate user-selected wall-color hints and stronger structural filtering, keeping a default-only result as a separate baseline. Determine whether hints are acceptable on these textured maps, rather than tuning against their supplied UVTT geometry. Automatic lights need a stricter contextual/shape criterion or supported-style policy.

Local review artifact: `/private/tmp/auto-wall-detection-review/review.html`. Generated assets stay local; rerun instructions and detector code are captured on this branch. The prototype ticket stays open pending human review.

## Upstream detector comparison after human rejection of initial quality

Added direct imports of upstream detect_walls and detect_lights at c11b8fa7ad5923d742722a063b3d4385f68527d8. Two settings: the detector function defaults, and initial GUI slider settings (Canny 255/106, blur 5, minimum area 0.1% of working image). Both use the same 1600px cap and fixed 3px polygon simplification as the comparison, not the full GUI/export processing or manual editing. OpenCV 5.0.0.93, NumPy 2.5.4, Python 3.15; OpenCV threads set to one. This is a detector baseline, not exact reproduction of a packaged upstream application.

| Map | Upstream initial GUI settings wall segments | Unreviewed reference coverage | Detection median ms |
| --- | ---: | ---: | ---: |
| Building | 45 | 35.8% | 115.4 |
| Tavern | 187 | 49.2% | 83.9 |
| Caverns | 298 | 8.1% | 139.4 |

Stronger filtering removes clutter but also misses major interior walls/cavern boundaries. Core defaults retain more reference length but produce 1,893 / 3,888 / 12,121 segments respectively. Brightness-based upstream lights yield 5 / 14 / 12 candidates; reference matches are 5 / 2 / 7, respectively, with reference validity still unreviewed. The controlled warm point is missed by the brightness detector.

Verdict: no accepted candidate. The rejection is about semantics/structure as well as simplification: merely making geometry shorter does not identify the right walls. Next decision is whether to invest in structural/region-aware image-only detection, accept explicit image-derived wall hints, or reconsider an optional learned segmentation backend. No evidence here establishes that threshold tuning alone will meet quality on all three styles.
