# UVTT contract and Bag of Mapping integration

Research for [Establish the UVTT contract and Bag of Mapping integration constraints](https://github.com/silkcom/auto-wall-rs/issues/3), 2026-11-06. Planning findings, not an implemented or compatibility-tested API.

## Recommendation

Return a typed, Serde-serializable UVTT data structure from a synchronous Rust detector. Keep image decoding, image embedding, filesystem access, and JSON writing at explicit boundaries. The server can consume the structure directly; the CLI embeds a map image and writes a complete `.uvtt` document. This matches the user's confirmed direction and the existing Bag of Mapping importer. Exact public signatures and error policy remain decisions for the API ticket.

Use format `0.3` initially to match the upstream producer, with an explicit compatibility fixture rather than assuming every importer treats fields identically. Default to origin `(0,0)`, positive integer pixels-per-grid, and fractional grid coordinates. Grid calibration and optional snapping are separate concerns. Do not silently snap geometry merely because a grid size was supplied.

## Evidence and wire contract

Arkenforge, a UVTT producer/consumer, documents JSON fields and square-based positions/sizes. Its developer documentation defines resolution, wall and object polylines, portals, environment, lights, and a base64 PNG/WebP image. Rotation is radians. It is producer documentation, not evidence of a separately governed normative standard. [Arkenforge developer info](https://arkenforge.com/universal-vtt-files/#:~:text=Universal%20VTT%20developer%20info).

Upstream pinned at `c11b8fa7ad5923d742722a063b3d4385f68527d8`:

| Field | Observed upstream behavior / proposed compatibility contract |
| --- | --- |
| `format` | Upstream emits numeric `0.3`; retain initially. |
| `resolution.map_origin` | Upstream forwards grid offsets; recommend zero origin initially to avoid inheriting uncertain offset units. |
| `resolution.map_size` | Original width/height divided by pixels-per-grid, retaining fractional values. |
| `resolution.pixels_per_grid` | Positive integer; upstream prefers overlay grid, then snapping grid, then 70. A good default is a scale convention, not inferred knowledge of the drawn grid. |
| `line_of_sight` | Arrays of `{x,y}` points; upstream emits two-point segments in grid units. |
| `objects_line_of_sight` | Upstream emits empty array. No object detection promised. |
| `portals` | Separate portal records; upstream conversion initializes empty and GUI adds doors manually. |
| `lights` | Position, range, intensity, color, shadows. Exclude private diagnostic keys. |
| `environment` | Upstream emits a fixed ambient color. This is a producer choice, not a detector truth; settle output defaults explicitly. |
| `image` | Upstream optionally PNG-encodes and base64-embeds; core should omit, CLI should include. |

Evidence: [upstream UVTT exporter](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/mask_editor.py#L970-L1080). Its Foundry conversion detour and `_preview_pixels` property are internal implementation details to avoid reproducing in the public result.

For an original image width `W`, height `H`, grid size `g`, wall endpoint `(px,py)` becomes `(px/g,py/g)` and map size becomes `(W/g,H/g)`. If detection resizes to `w × h`, undo that transform using actual axis scales before grid conversion; do not make the exported map dimensions depend on working-image resolution. These formulas are recommendations derived from the exporter and consumer coordinate math.

### Doors and lights

Upstream manual portal placement computes midpoint position, two endpoint bounds, `atan2(dy,dx)` rotation, `closed=true`, and `freestanding=false`. [Portal creation](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/gui/image_viewer.py#L1117-L1176).

Light detection stores pixel positions initially, ARGB-like eight-digit colors (`ff` plus RGB), heuristic range clamped to 1–5, intensity capped at 1, and shadows enabled. Position conversion is separate. The range heuristic divides a pixel-derived radius by a fixed 50 rather than the caller's actual grid size, so literal porting would bake in scale sensitivity. Treat range/intensity as configurable estimates, not recovered physical facts. [Light records and scaling](https://github.com/ThreeHats/auto-wall/blob/c11b8fa7ad5923d742722a063b3d4385f68527d8/src/wall_detection/light_detector.py#L113-L222).

## Bag of Mapping: verified local integration facts

Inspected sibling checkout `/Users/josephlarsen/Sites/bagofmapping`, HEAD `61ddf097c0fa2ede1d93f557877c3ba729126756`, remote `silkcom/bagofmapping`. Referenced Cargo/importer/selector/source files had no reported local modifications at inspection. Links below are pinned to that commit; access may require repository permission.

- Server package is `bom-server`, Rust edition 2024, declared Rust version 1.85. Dependencies include Axum 0.8, Tokio multithread runtime, Serde/Serde JSON, base64; no image or OpenCV dependency is currently declared. New crate MSRV/dependency choices should be compatible with the server's declared baseline, or explicitly require a toolchain change. [Cargo manifest](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/rust-server/Cargo.toml).
- Runtime uses `#[tokio::main]` and Axum serving. The detector should stay synchronous and runtime-agnostic; server integration should schedule CPU work off async executor threads. [Server entry](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/rust-server/src/main.rs).
- Existing UVTT import parses embedded image bytes, deletes `image`, and returns the remaining JSON as `vttData`. The worker transfers the image buffer separately. This directly supports no-image core output. [Importer worker](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/frontend/javascript/workers/vttFileImport.worker.js), [main-thread fallback](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/frontend/javascript/models/bomimages.model.js#L540-L563).
- Import setup uses pixels-per-grid for image zoom, map size for centering, and origin values for offset. Zero origin avoids ambiguity while establishing the contract. [Map import setup](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/frontend/javascript/components/Modal.ImageUpload.jsx#L690-L715).
- Runtime geometry multiplies UVTT points by `baseTokenWidth`. Polylines whose endpoints are within 0.2 grid units can be auto-closed. Initially prefer explicit two-point segments if such consumer modification would corrupt an intentionally open polyline. [Geometry conversion](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/frontend/javascript/models/fogRuntimeGeometry.js#L317-L335).
- Closed portals contribute blockers; open portals do not. **A detected door must replace overlapping permanent wall geometry**, otherwise opening it leaves the wall blocking sight. This is an integration inference from [wall selector](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/frontend/javascript/models/dynamicFogSelectors.js#L24-L38).
- Runtime lights require finite positions and positive finite range, interpreted in grid units. [Light source conversion](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/frontend/javascript/controllers/fogRuntimeSources.js#L240-L277).

### Embedding interoperability caveat

Bag of Mapping currently labels bare base64 as JPEG by default, but honors a data-URL MIME prefix. Upstream emits bare PNG base64; Arkenforge documents bare base64 PNG/WebP. Do not change the universal export to a data URL solely to fit this consumer without testing other importers. Prefer standard bare PNG and an explicit importer compatibility fixture; a Bag of Mapping MIME-sniffing fix can be separate integration work if needed. [Importer worker image extraction](https://github.com/silkcom/bagofmapping/blob/61ddf097c0fa2ede1d93f557877c3ba729126756/frontend/javascript/workers/vttFileImport.worker.js#L1-L44).

## Scheduling and resource boundaries

For initial integration, a bounded semaphore plus `spawn_blocking` is a simple candidate. Tokio specifically recommends limiting CPU-heavy blocking tasks; aborting the async handle does not stop an already running blocking job. Therefore request timeouts alone are not CPU cancellation. Image-size limits, bounded job admission, and possibly cooperative cancellation need explicit decisions if exposed to untrusted uploads. [Tokio `spawn_blocking`](https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html).

Keep CLI encoding and image embedding out of detection benchmarks. Reusing PNG input bytes can avoid re-encoding when no image transformation is required; other input formats need an explicit PNG/WebP export strategy. This is an efficiency recommendation, not measured performance evidence.

## Decisions still needed and verification

1. API input representation: borrowed decoded pixels plus optional byte-decoding convenience versus encoded bytes only; maximum decoded dimensions and supported image formats.
2. Concrete grid default and integer-only versus fractional user calibration; nonzero origin support; reject invalid calibration rather than producing invalid JSON.
3. Public error versus empty-detection semantics, diagnostic output, and optional door/light detectors.
4. Light color encoding and default environment settings verified against actual target importers, without assuming producer conventions are universal.
5. CLI interoperability fixtures: embedded PNG, fractional map dimensions, rescaled detection, closed/open door with wall gap, and known light position/range.
6. Server host concurrency/memory budgets and cancellation policy. Existing upload/storage integration point was not exhaustively traced, and no actual server integration or importer execution was performed.

No benchmark results, measured memory use, or cross-importer compatibility claims are made here.
