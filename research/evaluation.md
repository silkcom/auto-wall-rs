# Evaluation corpus, conservative detection, and performance measurement

Research for [Identify evaluation maps and conservative door-detection options](https://github.com/silkcom/auto-wall-rs/issues/4), 2026-11-06. Planning findings only: no detector, corpus, benchmark, or accuracy result was produced.

## Recommendation

Use original synthetic fixtures with exact geometry, generated One Page Dungeon maps with manually reviewed labels, and the user's actual clean dungeon maps. Evaluate false positives and sight-blocking topology separately. Treat automatic doors as an experimental, opt-in capability until held-out precision supports enabling it. A missing door must never silently punch an inferred opening in a wall. Set numeric quality and performance gates with the human after a baseline exists.

## Corpus sources and rights

- **One Page Dungeon** is a practical first public source: its author explicitly permits copying, modifying, and commercial use of generated images, with attribution appreciated but optional. Generate fresh maps, retain the exact exported PNG/SVG, generator URL/version, seed/options when available, and a copy/date of the permission statement. These are clean stylized maps; they do not establish performance on textured battle maps. [Author's permission](https://watabou.itch.io/one-page-dungeon).
- **Original synthetic fixtures** should encode expected geometry first, then render walls, doors, grids, and lights under controlled variation. This provides exact expected coordinates and avoids uncertain third-party image rights. This is a proposed fixture design, not an existing dataset. Include straight and diagonal walls, corners, curved rooms, touching components, thin barriers, narrow corridors, door symbols, blank maps, and light-colored non-light clutter. Apply rotations, resizing, anti-aliasing, grid overlays, and JPEG noise, retaining provenance.
- **Upstream's example** `data/input/CavernPitPublic-785x1024.jpg` exists, but a filename containing “Public” is not permission. Upstream has an MIT software license; no separate image-origin/asset license was established in this investigation. Use only after confirming asset rights; do not describe the image as CC0 or automatically covered by the source-code license. [Example](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/data/input/CavernPitPublic-785x1024.jpg), [license](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/LICENSE).
- **User maps** provide relevance missing from generated fixtures. Keep privately supplied maps local unless redistribution permission is known. Record whether each asset can enter the public repo; evaluation does not require publication.

Proposed initial size: roughly 20–30 distinct maps, with a small held-out subset. This is a starting proposal, not a statistically sufficient quality claim. Split by original map and visual style; crops, resizes, and recolorings of one map belong in the same split. Include maps with no doors/lights to expose false positives. Upstream fixtures alone are too sparse for a general quality claim.

## Ground truth and quality measures

These are project-specific proposed metrics rather than an assertion that a standard dungeon-wall benchmark exists.

Store original-pixel wall polylines, door endpoints/state where visually discernible, light positions, grid size if known, and uncertain/ignore regions in a separate annotation file. Annotate physical sight barriers, not every drawn edge: a thick wall may have two visible boundaries, while the desired VTT barrier may use one trace. Explicitly settle that annotation convention before scoring. Do not infer light range or open/closed door state when the image cannot determine it; those may be configured export defaults.

Review annotations before tuning. A second pass should check corners, wall junctions, grid-vs-wall ambiguity, doors, and intentionally open passages. Preserve uncertainty rather than force false ground truth.

| Output | Proposed measurement | Why it matters |
| --- | --- | --- |
| Walls | Length-weighted precision and recall within a declared geometric tolerance; symmetric point-to-polyline distances | Endpoint counts depend on segment splitting and can reward fragmentation |
| Connectivity | Expected blocked and open line-of-sight probe pairs, with annotated reason | Tiny gaps can cause major sight leaks despite good pixel overlap |
| Doors | One-to-one endpoint/span matches with position/orientation tolerance; precision, recall, false doors per map | A gap alone is not evidence of a door |
| Lights | One-to-one center matches with declared tolerance; precision, recall, false lights per map | White paper, labels, reflections, and bright floors are hard negatives |
| Geometry validity | Finite/in-bounds coordinates, zero-length segments, duplicate/overlapping walls, portal/wall consistency | Export validity is separate from recognition accuracy |

Express tolerances in grid units where known and document pixel fallback when unknown. Include doors closed and open in topology probes: closing a door should block its intended opening; opening it should not leave a permanent wall across the passage. Use ray/segment tests for line of sight. A flood-fill of walkable space can additionally detect room connectivity mistakes, but connectivity is not identical to visibility around corners.

Use a deterministic one-to-one matching policy, count duplicate detections as false positives, report raw TP/FP/FN and empty-class cases, and retain per-map results alongside aggregate scores. Conventional detection evaluation also explicitly matches detections and ground truth and tracks precision/recall; COCO's implementation is a useful reference, but box IoU/AP is not sufficient for thin walls. [COCO evaluator](https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py).

For precision-first acceptance, sweep thresholds on the tuning set, freeze them, then report held-out performance and feature coverage. An always-empty door detector has no false doors but offers no useful recall; report abstentions and recall rather than celebrating nominal precision. Set numeric gates only after viewing representative results. One aggregate score must not hide a catastrophic false wall or sight leak.

## Automatic doors: feasible experiments, unproven quality

Upstream creates portal objects through manual interaction; it does not supply a door classifier to port. [Manual portal creation](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/gui/image_viewer.py#L1117-L1176).

A bounded classical-CV experiment fits the deployment constraints:

1. Generate candidate regions near plausible wall gaps or door-shaped marks, with size bounds normalized by supplied grid size or estimated wall thickness. A gap is a candidate only, never sufficient classification.
2. Score structural evidence: wall context on both sides, plausible door width/orientation, rectangular leaf or swing arc, and interruption consistency. Keep candidate regions small to avoid scanning every template over the full image.
3. Optionally compare normalized patches against a small, explicitly supported door-symbol template bank across limited scales/orientations. Reject ambiguous matches, deduplicate overlapping candidates, and return no door when evidence is insufficient.
4. Validate doors and resulting wall openings together; retain baseline walls until the candidate is accepted. Preserve genuinely open passages rather than inventing doors to complete room boundaries.

This is a hypothesis for prototyping, not a finding that heuristic detection meets the user's accuracy goals. Template matching finds similar patches, not semantic doors; style changes, furniture, hatching, rotated symbols, and partial occlusion are likely failure cases. OpenCV documents template matching; pure Rust `imageproc` exposes serial, parallel, and masked matching, and Hough line detection, so these primitives do not inherently require Python, GPU, or downloaded model weights. [OpenCV tutorial](https://docs.opencv.org/5.0/tutorials/imgproc/histograms/template_matching/template_matching.html), [imageproc matching](https://docs.rs/imageproc/0.27.0/imageproc/template_matching/index.html), [imageproc Hough](https://docs.rs/imageproc/0.27.0/imageproc/hough/index.html).

Recommended decision: research/prototype this feature independently; keep an empty portal list valid; permit explicit caller hints later if useful. Do not claim a general solution from a single drawing style. If adequate precision cannot be demonstrated cheaply, defer automatic doors while preserving the UVTT portal data model.

For lights, brightness is evidence of bright pixels, not proof of an emitting object. Upstream supports brightness or selected-color masks plus contour filtering; include white labels and floors as negatives and allow conservative abstention. [Upstream light detector](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/light_detector.py#L11-L166).

## CPU latency and memory methodology

No measurements were run. Proposed benchmark contract:

- Pin fixture bytes, expected dimensions, source commit, Rust/toolchain and dependency versions, build profile/flags, CPU architecture/model, OS, available memory, CPU quota, thread count, and power mode. Measure Linux deployment hardware and macOS development independently.
- Use release builds. Time decoded-image detection separately from file read/decode, geometry conversion, JSON serialization, and CLI image encoding/base64/write. Include total CLI wall time, since embedding may dominate export even if detection improves.
- Include small, medium, and large examples (proposed 1, 4, 16 megapixels), plus images with many tiny components and highly fragmented contours. Report actual dimensions and segment/candidate counts. Scaling behavior matters as well as average duration.
- Criterion can supply repeatable warmed in-process measurements and comparisons. It uses warmup, sample measurement, analysis, and baseline comparison; use its confidence intervals for microbenchmark changes. Do not present its aggregate slope estimate as a request p95. [Criterion analysis](https://github.com/bheisler/criterion.rs/blob/master/book/src/analysis.md).
- Separately collect individual end-to-end invocation/request samples for median and p95, cold versus warm behavior, throughput, and concurrent load. Record sample count and variance; use sufficient samples before tail claims. Test concurrency 1 first, then bounded parallel requests, noting internal image-library threads to avoid oversubscription.
- Record peak RSS per fixture in a fresh process, not a cumulative reused-process maximum; include output size and allocation volume where useful. Linux `getrusage` exposes process peak resident memory in KiB; normalize platform units explicitly and document the macOS measurement tool. A long-lived server high-water mark is not per-request allocation. [Linux getrusage manual](https://man7.org/linux/man-pages/man2/getrusage.2.html).
- Freeze quality settings when comparing implementations. Measure optional downscaling as a separate quality/performance trade-off; map all output coordinates back to original image space. Do not trade away topology to produce a headline speedup.

Select numeric latency/memory budgets after baseline results and actual server hardware are known. Proposed priority remains: quality gate, single-image CPU latency, peak memory/concurrent throughput, then dependency footprint.

## Decisions still requiring the human

- Annotation convention for wall centerline versus visible edge and tolerated geometric error.
- Which actual map styles are first-version acceptance targets.
- Precision/recall/topology gates and supported image-size ceiling.
- Whether experimental automatic doors ship opt-in, stay outside the first release, or justify a prototype ticket.
- Concrete server latency, memory, and concurrency budgets after measurement.
