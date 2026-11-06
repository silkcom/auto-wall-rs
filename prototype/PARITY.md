# Auto-Wall parity comes first

The user changed the immediate milestone: match Auto-Wall's automatic behavior before optimizing or improving detection. The earlier simplified Rust modes and detector-only upstream modes are exploratory comparisons, not parity implementations. Their quality does not establish the upstream application's best achievable quality.

## Pinned reference

Upstream commit: `c11b8fa7ad5923d742722a063b3d4385f68527d8`.

`parity_reference.py` calls unmodified upstream methods:

1. `ImageProcessor.create_working_image`: 1500px cap, integer truncation of dimensions, OpenCV area resize, upstream scale-factor convention.
2. `ImageProcessor._update_image_internal`: slider/minimum-area interpretation (including its additional scale-squared adjustment), detection, optional merging, area filtering, edge splitting, small-fragment filtering, lights and original contour storage.
3. `ContourProcessor.scale_contours_to_original`: float32 division followed by int32 truncation, called by export.
4. `ExportPanel.preview_uvtt_walls`: upstream contour-to-UVTT conversion, including perimeter-relative simplification, subdivision/cap, endpoint merging, deduplication, collinear merging, original-image coordinates and grid units. The actual exporter also PNG-encodes the image; the capture removes image bytes and `_preview_pixels` only after generation.

The UI shell supplies explicit controls and disables rendering/history controls; it does not reimplement these algorithms. This is a headless automatic-path reference, not a recording of a manually edited GUI session. It bypasses the initial export dialog and supplies equivalent export settings. The dialog's refusal to generate when no contours exist is not an error-handling oracle; empty synthetic cases can still exercise the converter directly.

Profiles are explicit, never called best-quality presets:

- `startup`: initial sliders (blur 5, Canny 255/106, min-area slider 100, margin 0, no contour merge).
- `default`: named Default preset's settings (blur 3, Canny 50/150, min-area slider 124, margin 2, merge enabled, merge-distance slider 10).
- `black`: named solid-black detection settings, exact black selection and min-area slider 500.

For these comparisons, light detection is explicitly enabled with the GUI's brightness/area/merge settings. The GUI starts with lights disabled. Export uses sidebar defaults: simplification 0.0005, max length 50, cap 5000, endpoint merge 25, angle 1 degree, max gap 10, snapping disabled, overlay scale 70. These settings are recorded in every capture. User UVTT geometry does not enter detection or settings selection.

Manual mask edits/baking, drawing/deleting walls/doors, selected-color interaction, optional model-backed background removal, and custom hatching-removal configurations are not exercised by the three real-map baseline runs. Color-mask behavior has a controlled black-room fixture. Further parity coverage must identify the supported settings rather than claim all GUI features are covered.

## Reproduce

Prepare the pinned upstream checkout as described in README.md, then:

```sh
python3.12 -m venv /private/tmp/auto-wall-parity-env
/private/tmp/auto-wall-parity-env/bin/pip install -r prototype/parity-requirements.txt
/private/tmp/auto-wall-parity-env/bin/python prototype/parity_reference.py \
  prototype/fixtures/room.png /private/tmp/room-reference.json --profile default --lights
python3 prototype/compare_parity.py prototype/fixtures/room-default.json /private/tmp/room-reference.json
```

The environment is Python 3.12, NumPy 2.2.6 (within upstream's declared range), OpenCV 4.14.0, PyQt6 6.12.0. Exact installed packages are frozen in parity-requirements.txt. OpenCV is single-threaded for repeatability. GUI-only Qt/requests dependencies belong to this oracle, not the planned Rust library. The oracle requires tracked upstream source to be clean and at the pinned revision.

Synthetic room PNGs and captures in fixtures are original locally generated assets, not user maps. The dark room uses a 512px gray background and a 10px thick rectangular wall from pixels 90 through 421; the black variant changes the dark wall from RGB 20 to 0. Captures include timings as provenance, but timing differences are excluded from parity comparison.

## Parity gate

Before changing algorithms, compare the Rust candidate against the pinned oracle with identical decoded pixels, settings, versions and thread policy:

- Exact working dimensions and BGR buffer hash.
- Detection, merge, edge-split and postprocess contours. Exact stage comparison intentionally exposes ordering/rounding differences for investigation.
- Light output and final UVTT geometry/properties. The comparator ignores segment order and two-point segment direction for final walls; it ignores embedding and private preview data. It does not round away geometric differences.
- Preserve the segment-cap/order behavior, grid scale, merge semantics and upstream quirks initially. Document any deliberate fixes as divergences rather than silently calling them parity.
- Cover both edge and color modes, scale/no-scale, contour holes/borders, positive/negative lights, disabled lights, and export merging/snapping before claiming general automatic-path parity.

Repeat reference runs of the tavern Default profile produced identical stage contours and final UVTT geometry. This proves reference reproducibility in the captured environment, not Rust parity. Rust parity is still pending; none of the original Rust candidates satisfies this gate.

## Separate gates

1. Match the automatic Auto-Wall baseline at agreed settings.
2. Review whether that output is usable on all three user maps.
3. Optimize or improve detection, measuring intentional differences against both reference and user-quality criteria.

Automatic door detection remains new work because upstream doors are manually drawn.
