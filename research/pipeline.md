# Auto-Wall preliminary source scouting

Commit: c11b8fa7ad5923d742722a063b3d4385f68527d8

## Automatic walls

detect_walls copies input, either thresholds selected BGR colors and extracts hierarchical contours, or grayscale -> Gaussian blur -> Canny -> filled contour mask -> dilation -> connected components -> area filtering and contour extraction. Per-component masks cover the entire image.

Source: https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/detector.py#L5-L116

## Wall geometry

Douglas-Peucker contour simplification, closed-loop segment creation, subdivision by max length, max-wall cap, optional grid snapping, endpoint merging, deduplication and collinear merging. Intermediate Foundry records and random IDs are created even for UVTT export.

Source: https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/mask_editor.py#L223-L385

## Doors are manual

Mouse drawing creates portal endpoints and center, rotation, closed=true and freestanding=false. No automatic door detector exists in src. UVTT conversion initializes portals to an empty list.

Source: https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/gui/image_viewer.py#L1117-L1176

## Lights are heuristics

Brightness or selected-color thresholds -> morphological open/close -> contours -> area filter and centroid. Sample centroid color and brightness; estimate and clamp range, merge nearby candidates, scale pixel positions to grid units. This detects bright/color regions, not semantic torches.

Source: https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/light_detector.py#L11-L222

## UVTT

Exports format 0.3; resolution map_origin/map_size/pixels_per_grid; line_of_sight as two-point arrays in grid units; empty objects_line_of_sight and portals; ambient environment, lights; optional base64 PNG image; internal _preview_pixels data. Default grid scale falls back to 70. Actual interoperability should be researched separately rather than copied blindly.

Source: https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/mask_editor.py#L970-L1080

## Dependency separation

OpenCV and NumPy support the detection core. PyQt6 is GUI; scikit-learn KMeans is used by color selection (src/core/selection.py), not detect_walls; rembg and ONNX runtime support optional background removal. The full Python dependency list need not be reproduced in Rust.

Source: https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/requirements.txt

## License

MIT, copyright 2025 ThreeHats; retain notice in copies/substantial portions.

Source: https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/LICENSE

## Performance candidates (inference, unbenchmarked)

Endpoint merging repeatedly scans remaining points; collinear merging scans candidates; light merging is pairwise. Together with full-frame per-component masks, image copies, Foundry intermediate records, random IDs, and PNG recompression/base64, these are sensible profiling targets, not established bottlenecks.

Source: https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/mask_editor.py#L560-L807

## Rust implementation candidates

### Candidate A: native Rust image processing

Use `image` for decoding and typed image buffers, and evaluate `imageproc` for the detection primitives. The `image` documentation describes native Rust codecs, in-memory decoding, typed buffers, and decoder limits. A decoded-image entry point can therefore avoid forcing a server caller through filesystem I/O or repeated encoding. This is an API recommendation, not an existing project interface. [image API](https://docs.rs/image/0.25.10/image/)

Source inspection of imageproc commit `e825693df99237d9472fb06d8bfa3355ef51ef38` found Canny, binary contour extraction with outer/hole parent information, connected components, Douglas–Peucker approximation, and morphology. These cover the main categories of upstream operations, but do not establish equivalent behavior or acceptable speed. [Canny](https://github.com/image-rs/imageproc/blob/e825693df99237d9472fb06d8bfa3355ef51ef38/src/edges.rs#L9-L57), [contours](https://github.com/image-rs/imageproc/blob/e825693df99237d9472fb06d8bfa3355ef51ef38/src/contours.rs#L8-L68), [components](https://github.com/image-rs/imageproc/blob/e825693df99237d9472fb06d8bfa3355ef51ef38/src/region_labelling.rs#L122), [polygon approximation](https://github.com/image-rs/imageproc/blob/e825693df99237d9472fb06d8bfa3355ef51ef38/src/geometry.rs#L26), [morphology](https://github.com/image-rs/imageproc/blob/e825693df99237d9472fb06d8bfa3355ef51ef38/src/morphology.rs)

Important compatibility traps:

- imageproc Canny performs its own Gaussian blur with fixed sigma 1.4 and uses Euclidean Sobel gradient magnitude. Upstream separately applies configurable Gaussian blur, then calls OpenCV Canny with its defaults. Do not copy numeric threshold presets or add both blurs and assume parity. The source also allocates several intermediate buffers; pure Rust does not imply low peak memory. [imageproc Canny source](https://github.com/image-rs/imageproc/blob/e825693df99237d9472fb06d8bfa3355ef51ef38/src/edges.rs#L30-L57), [upstream call](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/detector.py#L64-L96)
- Morphology footprints, contour hierarchy, connectivity, rounding, and color-channel order need explicit tests against representative maps; matching function names are insufficient evidence of matching geometry. This is an inference from the distinct APIs.
- Current imageproc main declares version 0.28.0 and Rust 1.87, while the docs site returned 0.27.0 during this investigation. Pin an actual published version and inspect that version before implementation. Current-main findings are capability evidence, not a dependency lockfile. Its default features include Rayon, image defaults, text, and FFT; disable unneeded defaults. [manifest](https://github.com/image-rs/imageproc/blob/e825693df99237d9472fb06d8bfa3355ef51ef38/Cargo.toml#L1-L38)

### Candidate B: Rust bindings to native OpenCV

Use the `opencv` crate with the minimum needed modules (principally `imgproc`; add `imgcodecs` only if decoding through OpenCV is chosen). This preserves access to the same primitive family as Python upstream, though parameter and version differences still need testing. The bindings require installed OpenCV and Clang/libclang for generation and document platform-specific linking/discovery. This brings native build and deployment obligations; it is not a standalone pure-Rust implementation. [binding README](https://github.com/twistedfall/opencv-rust/blob/901d7a221b6172846f77d38c2beb868fab18ef2c/README.md), [installation](https://github.com/twistedfall/opencv-rust/blob/901d7a221b6172846f77d38c2beb868fab18ef2c/INSTALL.md), [module features](https://github.com/twistedfall/opencv-rust/blob/901d7a221b6172846f77d38c2beb868fab18ef2c/Cargo.toml#L75-L231)

Do not assume rewriting Python calls in Rust makes OpenCV kernels faster: those calls already execute native image-processing code. Any speedup would need to come from orchestration, fewer allocations/copies, better geometry algorithms, changed quality settings, or a different measured kernel implementation. This is architectural inference, not a measured result.

## Recommended evaluation route

1. Prefer a small CPU-only library with decoded-image input and structured results, plus a thin CLI; keep image embedding/serialization outside the geometry hot path. This follows the user's requested in-process server and CLI usage, and avoids upstream's unnecessary Foundry intermediate representation.
2. Evaluate native Rust (`image` plus selected `imageproc` primitives) first for a simple deployment baseline. Compare a minimal native-OpenCV candidate only where measurements or unacceptable detection behavior justify it. Do not commit to either backend as fastest before benchmarking.
3. For walls, compare color-mask and edge-mask routes on actual target maps. Color selection needs explicit input hints or a separately evaluated automatic selection strategy; upstream's interactive color picker is not an automatic default-selection algorithm.
4. Keep lights explicitly heuristic and configurable. Require conservative evidence before outputting automatic doors; upstream provides no detector to transplant. Door recognition deserves an independent investigation/prototype and quality gate.
5. Replace global endpoint scans with a spatial lookup candidate and collinear-candidate scans with indexed/grouped candidates only when a prototype or profile justifies the added complexity. Avoid subdividing long straight walls just to merge them again. These are hypotheses, not implemented optimizations.
6. Measure release builds on the same decoded inputs and fixed quality settings. Separate decode, preprocessing, wall masks, contours, simplification/connectivity, lights/doors, and serialization/image embedding. Record wall/light/door quality, segment counts, elapsed time, peak memory, input dimensions, hardware, thread count, and concurrent-job effects. No benchmark was executed in this investigation.

## What remains undecided

- Representative corpus and acceptable false walls, omitted walls, false doors, missed doors, and false/missed lights.
- Whether door output must be nonempty in the first useful version, or may conservatively return no doors when uncertain.
- Priority among latency, memory, throughput, output geometry size, and native dependency footprint; numeric budgets depend on target hardware and maps.
- CPU-only versus optional accelerated/model-based approaches if heuristics cannot satisfy door/light quality.
- Default detection settings, input hints, UVTT grid/coordinate contract, image embedding behavior, and downstream importer compatibility.

This investigation supplies candidates and risks. It does not decide quality/performance tradeoffs for the user or implement the product.
