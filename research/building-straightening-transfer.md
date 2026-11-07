# Straightening and frozen building transfer

The user rejects every building candidate as unacceptable. Hard negatives is the closest; balanced+portalchecks is the next comparison. Preserve those results, not the former baseline, as the leading experiments. The user specifically requests straighter building walls and evaluation on a different map without tuning to it.

## Geometry-only change on Conyberry

The new optional straight-grid mode simplifies each traced skeleton chain within0.12grid units in source pixels (5.8800px with the unchanged49.0002grid hint). Existing mode remains0.5working pixels. This is scale-limited piecewise straight approximation, not a new wall detector. It preserves chain endpoints/junction identities and does not force axis alignment or add connections between components. Small corners can be approximated within the tolerance. It cannot recover missed walls or remove semantically wrong furniture blockers.

| Conyberry variant | Raw segments → straight segments | Held-out P/R at0.2grid, raw → straight | Held-out leaks / false blockers, raw → straight |
|---|---:|---|---|
|Hard negatives|3053→1572|71.86/88.64%→72.63/87.54%|52/12→54/14|
|Balanced|2518→1232|76.59/87.35%→77.06/86.23%|57/7→58/7|

The visual lines are less jagged and contain fewer redundant joints. Quality is NOT solved: coverage drops slightly and visibility does not improve. No models, labels or class masks were changed. Same-map held-out scores remain development validation. Doors remain unreliable.

Checks cover a jittered straight wall, a non-axis-aligned wall, a room ring, an open doorway and blank input. Straightening does not replace the original candidates.

## Different-map evaluation with frozen settings

[User-supplied full image](https://i.etsystatic.com/54312091/r/il/d51bd1/7440454037/il_fullxfull.7440454037_c8fq.jpg):3000×3000, SHA256d03ce0131e41335a18c03531208c5349e18ccee1b3d546ff1d1c93754158dbcc. Source image and all overlays remain private outside git. This image was visually inspected but supplies no training samples or reference geometry.

Before prediction, the private manifest recorded model hashes, geometry-code hash and settings. Both frozen models were run with raw and straightened extraction. The Conyberry grid hint49.0002was retained unchanged; the actual new-map grid is unknown. No image-specific settings, color corrections, training labels or retraining were applied after observing the failure.

| Frozen model | Predicted background fraction | Raw → straight segments | Supported portals |
|---|---:|---:|---:|
|Hard negatives|99.9733%|33→25|0|
|Balanced|99.9461%|71→50|0|

Both miss almost all visible building walls. These class fractions and segment counts describe output, NOT numeric correctness. No P/R or visibility score is invented without reference geometry. Failure already exists in the predicted raster, so straightening cannot recover the missing walls. No ablation identifies which appearance/scale/training limitation dominates.

The raw and straightened outputs are in the review as a separate no-reference case. Exact reruns reproduce the hard-negative class raster and geometry. The new image remains evaluation-only: further work must improve general building perception rather than optimize this image's output. This is direct evidence the current appearance classifier is not general enough.

## Reproduction and cost

`python prototype/building_transfer.py IMAGE MODEL OUTPUT --grid GRID` runs one image/model-only pipeline with both extraction modes. No reference argument or training step exists. The original trained models remain fixed. Private initial manifests/results are separate from this generic replay helper.

Local CPU only; zero paid vision-label calls per map. Roughly4.8–5.1seconds per frozen model on this image, with raw/straight geometry sharing its prediction. No production latency or dollar hosting estimate is established. Review timing labels distinguish geometry-only Conyberry timings from full model inference. Development-agent usage is outside the per-map label cost table.
