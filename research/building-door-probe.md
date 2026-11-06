# Building and door feasibility probe

The existing floor/solid segmentation architecture can share an image encoder and feature extraction across caves and buildings, but its binary region contour output cannot represent a door as a separate movable barrier. The current cave-trained model also has no established building generalization. A common pipeline needs at least structural-wall and door evidence, with door proposals scored against wall context before changing topology. This is an architectural conclusion from the inspected prototype, not a successful building detector.

## Sources inspected

- [OpenCV Hough transform documentation](https://docs.opencv.org/4.13.0/d9/db0/tutorial_hough_lines.html): HoughLinesP produces straight-line segment endpoints from edge evidence. It does not supply object semantics. This probe uses Canny followed by probabilistic Hough detection as described there.
- [Upstream wall detector source](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/detector.py): inspected local clone at this revision. It uses edge/contour or selected-color contours and component processing. Its wall detector does not infer door objects.
- [Upstream portal UI source](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/core/mode_manager.py): draw-portals mode explicitly instructs users to click and drag doors/portals. Existing portal editing is not an automatic door-detection baseline.
- Local `prototype/cave_segmentation/candidate.py`: image-only features feed a binary forest; morphology and closed contour approximation produce walls. Open, thin structure and movable barriers require different output treatment. The cave candidate README already records open-feature limitations.

## Frozen small experiment

`prototype/building_door_probe.py` accepts only a raster and output directory. No map name, coordinates, reference path, grid metadata, model or style switch is consumed by inference. Both private images use identical constants. Images are reduced to a maximum dimension of 1600. Canny edges feed HoughLinesP. Two near-collinear segments with an 8–45 working-pixel interruption form one gap. A proposal requires a second parallel interruption 3–12 working pixels away, with aligned ends and long support on both sides. Deduplication merges nearby proposals. The result is a **proposal**, never an accepted door, and no wall is cut.

This tests whether a narrow, conservative four-flank geometric requirement is sufficient. It is deliberately not a learned detector and does not establish semantic door confidence. Constants were chosen before reading either reference in this probe and were not tuned against scores. Grid information was loaded only in a separate scoring process after raster inference completed.

Private runnable command (installed OpenCV/NumPy environment; no installation):

```
/private/tmp/auto-wall-upstream-env/bin/python prototype/building_door_probe.py IMAGE PRIVATE_OUTPUT_DIRECTORY
```

A uniform blank-image assertion runs on each invocation. Private outputs live under `/private/tmp/auto-wall-building-probe/`; no private raster, reference geometry or learned asset is part of this note or script.

## Results and visual evidence

| Raster | Hough segments | Single gaps | Paired proposals | Reference portals | Matched proposals |
| --- | ---: | ---: | ---: | ---: | ---: |
| Building | 77 | 9 | 0 | 8 | 0 |
| Tavern | 1076 | 251 | 1 | 12 | 0 |

Measured single-run image processing was about 0.10s and 1.35s respectively on this machine, excluding decode/output and the blank assertion. No production latency claim follows from two runs.

Scoring loaded the corresponding local UVTT documents **after** proposal JSON existed. It requires both endpoints to fall within 0.2 grid units, allowing endpoint reversal. Building tolerance was 30 pixels; Tavern 24 pixels. Tavern's sole candidate had a nearest reference endpoint error of approximately 485 pixels, so it did not match. These UVTT portals are reference annotations, not independently audited ground truth. Reference counts and scores alone cannot prove pixel truth.

Visual inspection of `/private/tmp/auto-wall-building-probe/tavern/preview.jpg` shows the only marked proposal on a chair beside a table, away from a wall. Building has no marked candidate. Its thin rendered walls contain multiple doorway/door-like symbols, while wood flooring, furniture and tree occlusion break simple edge assumptions. Thus even the conservative four-flank requirement admits furniture and misses the Building reference portals. The output is unsuitable for automatic acceptance. Zero Building proposals demonstrates conservative abstention, not a working door solution.

## Implication for the common pipeline

Use one image-only feature/segmentation pipeline with multiple output classes or heads: traversable regions, structural walls, and door candidates. Add a shared wall-context check so isolated chair/table geometry cannot become a door, and retain uncertain wall continuity rather than opening a false passage. A door class needs independent building examples and leave-map-out validation; cave-only training cannot demonstrate it. The proposed classes and context check are follow-up design work, not implemented here.

Binary floor contour extraction can remain a common stage, but it must preserve thin/open structure and permit a separate portal primitive. Merely enabling Hough gap proposals after the present contour stage does not meet the building requirement. No per-map detector routing or hand-authored coordinates were introduced.

An attempted run of the older binary random-forest candidate against Building could not start because the available upstream OpenCV environment lacks `cv2.ml`. No dependency was installed and no Building segmentation quality claim is made from that attempt. This probe covers door proposal feasibility only; it does not establish all-three-cave plus Building segmentation success.
