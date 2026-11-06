# One image-only wall and door pipeline: bounded next step

Research date: 2026-11-06. Source review only: no paid requests, model downloads, new training, or accuracy claims. Existing experiments are development evidence. The target is one algorithm/configuration on all three caves and building maps, with map-specific semantic observations allowed and no inference reference vectors. Later user feedback permits a portfolio of candidates with user selection; no automatic ranking is required for that direction.

## What is actually failing

The accepted frost Semantic round1 and unseen textured Semantic round2/local cleanup show that sparse image interpretation plus inexpensive geometry can work on different styles. They do not establish robustness. The canonical boundary RF+ICM remains the closest canonical result; its cross-style failure shows appearance generalization is still missing. More iterations or one-map training do not supply that information. See [experiment results](cave-experiment-results.md).

There is also a concrete untested architectural confound in [semantic_infer.py](../prototype/cave_segmentation/semantic_infer.py):

1. The RF uses multiscale color/texture and produces a probability.
2. Its probability is thresholded at 0.5 into probable foreground/background labels; only sparse semantic seeds become hard labels.
3. OpenCV GrabCut fits its own global color models and optimizes their labeling. The RF probabilities are not its fixed unary costs.
4. A 3×3 morphological closing is then applied, followed by area filtering and contour simplification.

OpenCV documents GMM appearance models and graph optimization, with hard foreground/background labels fixed during segmentation. Therefore this pipeline does not test “texture RF probabilities plus a spatial prior” directly. Texture confidence can disappear after thresholding, and a global appearance refit can propagate local sample changes across the map. This is a source-backed mechanism; whether it explains the canonical failure must be measured. [OpenCV GrabCut](https://docs.opencv.org/4.x/d8/d83/tutorial_py_grabcut.html).

The later audit regression is consistent with global coupling and biased sample frequency, but does not identify the relative contribution of wrong labels, inadequate features, class prior, GrabCut, or morphology. Separate those causes before adding models.

## A common foundation, with an explicit representation limit

Recommended architecture hypothesis: semantic observations → local appearance probabilities and boundary evidence → constrained raster labeling → wall graph → typed portals. Use the same stages everywhere. Curves and straight walls should emerge from evidence; a map-style router is unnecessary.

Keep two output primitives: closed interfaces around opaque regions, and optional open blocking paths. A binary floor/solid mask cannot express an isolated one-sided cliff line or movable door correctly. A door also needs identity and a span anchored to structural walls; a contour around a painted door leaf is not its portal. This matches the repository's Wall/Door glossary. Floor occupancy and light/visibility blocking are related targets, not interchangeable annotations.

Use the existing RF/CPU solver as the initial appearance component. Per-map semantic labels are an automatic adaptation mechanism, not a separately hand-selected algorithm. However, their selection policy and budget must be frozen across maps. If this fails, the missing ingredient may be representative semantic supervision, rather than a stronger contour algorithm.

## Smallest experiment: isolate the solver before changing perception

Run the exact accepted label sets and their existing trained RF probabilities on all three caves. Do not request new labels. Produce three comparable outputs with identical extraction, no morphology, no component removal, and original hard seeds preserved:

- Thresholded RF, as the perception baseline.
- Existing global GrabCut, as the current appearance-refitting baseline.
- Four-pass fixed-unary ICM using `-log(p)` and `-log(1-p)` plus the existing contrast-sensitive prior from [structured_refine.py](../prototype/cave_segmentation/structured_refine.py). Add explicit hard-seed protection; its current confidence thresholds are not a substitute for seed identity.

Keep old preferred outputs beside these; this ablation is not an automatic promotion. Reusing the already-failed *canonical-trained* forest with ICM does not answer this question: this experiment uses each map's image-only semantic RF and isolates what the downstream solver does to it.

Record raw-to-final changed pixels, seed violations, runtime, closed/open passage changes, missing islands, and boundary P/R where reference exists. For the unpaired map, show fixed native-resolution crops and assess visibly false barriers/missing barriers without inventing reference metrics. Include extraction-only changes separately if disabling morphology changes topology. No per-map parameter tuning.

Interpretation gates:

- If raw RF already misses the canonical tunnels or barriers, stop solver work: it is a perception/annotation problem.
- If raw RF is good and GrabCut destroys it, retain fixed semantic unaries; compare exact binary graph cut only if ICM gets stuck with otherwise credible evidence. No need to implement a new solver first.
- If all masks identify the same wrong boundary convention, revise semantic supervision, not smoothness.
- If unsimplified boundaries are good but vectors fail, isolate extraction/simplification at the same grid-relative tolerance.

Do not claim success merely because component counts stay unchanged: a wrong barrier can move while counts remain fixed, and a correct edit can legitimately alter a count.

## Doors: practical geometry without pretending gaps are semantic labels

CubiCasa's upstream code is useful architectural evidence. Its `get_opening_polygon` extracts opening endpoint heatmaps near wall evidence, pairs endpoints, and uses segmentation evidence to classify openings; `adjust_door_points` aligns endpoints to associated walls. It separates detecting a door from constructing its geometry. Its implementation contains horizontal/vertical assumptions, so copying it wholesale would constrain diagonal buildings and caves. [CubiCasa postprocessing source](https://github.com/CubiCasa/CubiCasa5k/blob/master/floortrans/post_prosessing.py).

Minimal later door experiment: on a small building example, automatically propose spans between nearby wall ends and around semantic door detections; have the same bounded semantic pass distinguish door, open passage, wall, and unknown in numbered crops. Locally fit the span against nearby wall evidence and attach its ends to the wall graph. Keep unsupported candidates unknown. Geometry alone cannot reliably distinguish an open arch, broken wall, window, and door. Closed painted doors also require proposals beyond existing gaps. This is a hypothesis, not a tested detector.

OpenCV's installed line-segment detector can propose local straight supports and returns line coordinates/width/precision; those are image measurements, not door recognition. Use it only inside candidate neighborhoods, and retain arbitrary-angle lines. Do not impose global Manhattan snapping or straighten cave outlines. [OpenCV LineSegmentDetector](https://docs.opencv.org/4.x/db/d73/classcv_1_1LineSegmentDetector.html).

DeepFloorplan likewise supervises wall and door/window boundary labels separately from room labels. That supports a common semantic-boundary representation, but its architectural-floorplan training domain and old TensorFlow GPU stack do not establish battle-map transfer or CPU suitability. CubiCasa's repository license is CC BY-NC 4.0; do not assume its dataset/model is a commercial drop-in. Neither system merits a large download for this immediate ablation. [DeepFloorplan upstream](https://github.com/zlzeng/DeepFloorplan), [CubiCasa license](https://github.com/CubiCasa/CubiCasa5k/blob/master/LICENSE).

## What data changes the decision

Before a new shared neural model, collect paired examples across art styles and building geometries, with map/artist-level splits. Include diagonal walls, open and closed doors, arches, windows, rock islands, thin tunnels, water banks, furniture, and visible faces/shadows. Specify which should block visibility. Preserve portal identity/endpoints and open LOS paths rather than converting every reference into filled polygons. Hold out complete maps; more correlated pixels from one map cannot demonstrate transfer.

A first useful annotation packet is a frozen set of failure crops across all three caves plus one building, each containing a target blocking-boundary sketch/class and uncertainty flag. Use these for development diagnosis only. A new blind map is needed before any generalization claim. The existing unpaired textured map has already influenced development and is not an untouched holdout.

The observed semantic label costs are below the requested $0.50–$1 per map in these experiments, but the frost case inherited warm context. A production budget must meter cold input, output/reasoning, and retries. Prefer one overview plus a bounded candidate-crop batch, with fixed token/call ceilings; a dollar target does not establish that the semantic information will be sufficient. CPU timing must include feature extraction and vectorization, not just four solver iterations. [Measured costs and limits](cave-experiment-results.md).

Decision: run the no-new-label solver ablation first. If perception is already wrong, prioritize a cross-style boundary/door annotation contract and representative data. Local semantic correction with spatially restricted influence is a sensible subsequent hypothesis; another global refit or generic segmenter is not yet justified by the evidence.
