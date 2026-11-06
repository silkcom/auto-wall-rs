# Dedicated building-band model: bounded experiment

A dedicated supervised building model is mechanically feasible, but this two-map model does **not** transfer to the blind Conyberry image. It reproduces recognizable training boundaries while missing nearly all visible building walls in Conyberry and placing portal proposals on terrain. This does not support a usable new building detector or door-accuracy claim. No follow-up tuning was performed after viewing the blind output.

## Scope and sources

Implementation: [prototype/building_model.py](../prototype/building_model.py). Reuses the existing original multiscale appearance features from [candidate.py](../prototype/cave_segmentation/candidate.py); uses installed OpenCV/numpy only. No downloaded model, paid API, map-specific inference coordinates, manual labels, AI point annotations, or Conyberry reference geometry.

Training sources and authoritative geometry:

| Development image | Reference | Dimensions |
| --- | --- | --- |
| `/private/tmp/auto-wall-detection-review/building.input` | `/Users/josephlarsen/Downloads/ExportingVtt.dd2vtt` | 4350 × 3300 |
| `/private/tmp/auto-wall-detection-review/tavern.input` | `/Users/josephlarsen/Downloads/The Pig and Whistle tavern.uvtt` | 3840 × 2640 |

Blind test: `/Users/josephlarsen/Sites/bagofmapping/static/images/partners/morvold/RestoredConyberryPhase3Large.jpg`, **4054 × 2846**, SHA256 `11c87324bf8d73105e85bb19278c421b864578a915825f409774faed82797592`. This is the complete original image, not a thumbnail or crop. Conyberry was never passed to training or labeling.

The primary references themselves establish important conventions: building has nine `line_of_sight` paths and eight portals; tavern has zero `line_of_sight` paths, 58 `objects_line_of_sight` paths, and 12 portals. Both LOS groups therefore contribute wall supervision. These include object boundaries, not exclusively building shells. Portal `bounds` are their segment coordinates. Tavern `position` values do not consistently describe the midpoint, so they are not used. `closed` is a state, not sufficient proof of movable-door semantics. All portal annotations remain a separate **portal-band** class, never relabeled as doors.

## One frozen experiment

- Quarter-resolution features: existing 23 LAB/local-mean/local-standard-deviation/gradient/grayscale channels plus eight absolute directional-gradient channels (horizontal, vertical, two diagonals at Gaussian sigma 1 and 3).
- Three classes: background, wall band, portal band. Rasterize each LOS path as consecutive **open polyline segments**, without filling interiors or implicitly closing paths. Explicit repeated endpoints in the source still represent closed paths naturally.
- Target band thickness: three working pixels, nominally 12 original pixels. Exclude the surrounding uncertainty shoulder using a 9 × 9 dilation. Exclude adjacent/overlapping wall and portal bands using 3 × 3 dilations. Uncertain samples never become background targets.
- Deterministic seed 42; at most 16,000 samples per map per class, 52,703 total. RF: 65 trees, maximum depth 18, minimum sample count 12, six active variables. No parameter search.
- Identical inference for both development maps and Conyberry: image features → frozen forest votes → largest-probability class, retained only at probability ≥ 0.55. No floor filling, ICM, hand repair, reference access, or map-specific branch.
- Output is a **raster proposal band**, not exported LOS geometry. The required final geometry is one centerline between the two visible wall faces, never two face traces or a closed ribbon. A future wall-material segmentation needs paired-boundary centerline extraction or skeleton/graph reconstruction; verified door spans must attach to centerline endpoints and cut the permanent blocker. This run stops before that stage. Reliable centerlines, connectivity, open endpoints, and door semantics remain unsolved; vectorizing failed bands would not make them usable walls.

Frozen model SHA256: `bddb2ae7b1b9a24e699bfdd478b0df8d51e959f2c467a2e5c4170d3ec1839889`.

## Observations against visible source images

Source on the left, predicted green wall bands and orange portal bands on the right:

- [Building comparison](/private/tmp/auto-wall-building-model/building/comparison.jpg): exterior rectangle and portal gaps are recognizable. This is training reproduction, not independent validation.
- [Tavern comparison](/private/tmp/auto-wall-building-model/tavern/comparison.jpg): exterior walls, partitions, bar, stair and object LOS boundaries appear; several small object/texture responses remain. Again this is development data.
- [Conyberry comparison](/private/tmp/auto-wall-building-model/conyberry/comparison.jpg): most visible exterior/interior walls are absent. Magenta responses scatter across roads and terrain, with occasional building responses. The result is unsuitable for automated tracing or door placement.

| Image | Wall band pixels | Portal band pixels | Inference |
| --- | ---: | ---: | ---: |
| Building, development | 0.489% | 0.226% | 5.01 s |
| Tavern, development | 9.163% | 0.167% | 5.60 s |
| Conyberry, blind test | 0.166% | 0.659% | 6.00 s |

Fractions are coverage, **not accuracy**. No blind reference exists in this experiment, so there is no Conyberry precision/recall score. The visual comparison supports failure, not a numerical estimate of generalization. Different art style, smaller buildings relative to the fixed feature windows, and thin supervision aligned to annotated LOS rather than a consistent visual wall-material center are plausible causes, not isolated causal findings. Quarter-resolution reduction can also merge the two visible wall faces on small buildings. No ablation separated these hypotheses, and visually adequate reproduction of training maps does not resolve them.

## Reproduce and inspect

All private artifacts are under `/private/tmp/auto-wall-building-model`: `train.json`, `training.json` (training hashes and per-class counts), `model.xml`, and per-image `source.jpg`, `overlay.jpg`, `comparison.jpg`, `classes.png`, `probability-1.png`, `probability-2.png`, `inference.json`. The model and image hashes agree across all three inference reports.

```sh
/private/tmp/auto-wall-parity-env/bin/python prototype/building_model.py selfcheck
/private/tmp/auto-wall-parity-env/bin/python prototype/building_model.py train /private/tmp/auto-wall-building-model/train.json /private/tmp/auto-wall-building-model/model.xml /private/tmp/auto-wall-building-model/training.json
/private/tmp/auto-wall-parity-env/bin/python prototype/building_model.py infer IMAGE /private/tmp/auto-wall-building-model/model.xml OUTPUT_DIRECTORY
```

Checks passed: synthetic open-path interior remains background; synthetic wall and portal bands retain separate classes; expected 31-feature shape; inference on a synthetic image with the reference-labeling function replaced by a hard failure. The CLI's `infer` subcommand accepts no reference argument. Source comparisons for all three maps were visually inspected.

A useful next training effort would need multiple independently annotated building maps covering art styles and map scales, explicit wall/object/portal conventions, and a reserved map-level evaluation set. Conyberry is now observed test evidence and should not silently become a tuning set. This bounded run establishes the target representation and clean train/infer boundary; it does not establish sufficient training data or a successful model split.
