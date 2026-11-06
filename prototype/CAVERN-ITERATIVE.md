# Cavern iterative alignment and wall-mass inset

The user clarified the desired workflow: establish one geometry, inspect it against the raster, then move existing points/add joints and repair local topology rather than redraw the map each pass. Up to ten passes were authorized, with sight barriers slightly inside solid wall mass so the visible face remains visible. A fresh-context subagent's ongoing calibrated reconstruction was steered into this workflow.

## Diagnosis

The canonical source is 3600×4500. An independent SIFT registration check found 1463 inliers between a 900×1125 source preview and the 880×1100 review thumbnail. Expected scale was .977777; fitted scale .97705 with approximately [.32,.41] px translation. Quadrant median residuals ranged .282–.309 thumbnail pixels, including southeast. No accumulating renderer stretch/offset was established.

Wrong physical contour choices and misplaced manual vertices were demonstrated. Historical tool-display mismeasurement remains a hypothesis, not an established scale bug. A new hazard was found in interior grid labels printed below their grid lines; final inspection tiles use border axes at exact source tick locations. Native 300–900px crops with explicit origins replaced coarse overview coordinate guesses. Final bordered tiles contain 900×900 source pixels plus a 55px left and 25px top annotation margin; those margins are not part of wall coordinates.

## Ten incremental passes

There are ten saved snapshots: baseline pass01 plus nine local inspect/edit/render/reinspect cycles. Named path identifiers remain stable; changes log vertex movement, inserted joints, local additions, and retired mistaken interpretations. Inset was chosen by physical region: enclosing boundaries move outward into enclosing rock; obstacle footprints shrink inward into rock. Typical inset is 8–20 native pixels (NW enclosure about20; significant obstacles about12), not a single global dilation.

Independent pass06 review identified four improper crossings between two lower-island paths, including a return that climbed through raised floor instead of following the water-facing rock hook. The same paths were locally corrected. A reproducible crossing check goes from four crossings at pass06 to none at pass09. A tail bulging into the river was also moved onto the actual rock, and pass10 repaired shared joints. No broad affine warp was applied.

## Result and verification

Final: 2960 unique wall segments, 127 active named paths, no visible doors, and 16 unchanged light sources. Eight source-selected floor/opening checks pass on the final result; baseline fails three. Major rock-center and coordinate/bounds/duplicate checks passed. This is not an exhaustive independent topology/accuracy benchmark.

One ambiguous exposed tunnel/room termination near (1803,3188) remains flagged; stylized grey overhang/spine opacity remains approximate. Perfect alignment and absence of every LOS leak are not claimed. No source UVTT wall arrays were read; prior AI drafts and the user's screenshot feedback were permitted inputs.

The local review adds `Caverns · iterative alignment + wall inset` and an inspection-pass selector for all ten snapshots. The final pass is selected by default; changing passes preserves the same source map and permits visibility comparisons. Switching maps hides irrelevant pass controls. Browser navigation, snapshot selection and console checks passed.

## Local evidence and accounting

Private assets: `/private/tmp/auto-wall-ai-v4/caverns/` contains result.json, diagnostic.md, all pass snapshots/overlays/changes, final native tiles, validation reports and scripts. `/private/tmp/auto-wall-ai-v4/renderer-registration.json` and crossing-regression.json hold parent checks. None of these image/coordinate assets are uploaded or committed.

The completed isolated agent's measured tokens and supplied-rate costs are in `/private/tmp/auto-wall-ai-v4/token-cost.md` and token-cost.json. They include diagnosis, source inspection, all refinements, feedback and the agent's final response; parent coordination/integration is excluded. Cached reads are included in reported input totals. Rates are user-supplied, not inferred from plan pricing. Rebuild: `python3 prototype/add_cavern_pass.py --revision 4`, requiring the private manifest and outputs.

This prototype does not change the primary Auto-Wall-parity milestone or establish production AI inference price/accuracy.
