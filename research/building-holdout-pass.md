# Whole-building spatial development pass

The fixed 31-feature RF now learns from accepted Conyberry annotations plus the original two maps. Its heldout wall-band recall reaches 89%, but door recall remains unusably low. The single wider-context variant does not improve the balance. The later fixed hard-negative refinement below reduces scenery responses but trades away heldout wall recall and increases false door responses.

## Frozen split and leakage controls

Accepted hand-drawn UVTT walls and portals form a raster graph at quarter resolution, with a 3×3 dilation to join nearly coincident endpoints. Connected components become bounding boxes; intersecting and nested boxes merge repeatedly until stable. The resulting 14 groups sort by x-center (then y-center), alternating train/heldout without manual selection. Seven whole groups belong to each partition. Bounding boxes gain a six-pixel halo for nearby negatives. Every heldout box remains complete; training pixels within 52 quarter-resolution pixels (208 source pixels) of a heldout box are excluded. A runtime assertion verifies that both partitions' 26-pixel-radius receptive windows are disjoint. Some training boxes can lose eligible pixels to this guard; no heldout group supplies training labels.

The split was written before either model trained and its SHA-256 is stored in both provenance reports. The original 31 features use at most a 48-source-pixel radius; the 33-feature variant adds grayscale mean and standard deviation in a 49×49 quarter-resolution window (96-source-pixel radius). The common 104-source-pixel guard includes resizing support. No XY coordinates, map identity, reference-derived input feature, or reference-at-inference feature enters either model.

Both models use identical 65-tree RTrees, depth 18, minimum samples 12, six active variables, seed 42, at most 16,000 samples per class per source, and the existing 0.55 max-vote threshold. Training negatives come from the guarded training boxes and the two earlier maps. These include local non-wall appearance, but this pass has no semantic fence/road annotations; it cannot claim measured fence-specific rejection.

## Band metrics

These are quarter-resolution raster band scores against the existing three-pixel-wide training objective, excluding ambiguous shoulders and wall/door overlap. They do not measure vector geometry, connectivity, door state, or actual LOS correctness. Conyberry is now spatial development validation, not an independent map generalization test.

| Model | Wall recall | Wall precision | Door recall | Door precision | Heldout background classified wall/door | Remote terrain wall / door pixels |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 89.24% | 89.73% | 3.68% | 49.47% | 1256 / 54919 | 1658 / 0 |
| context | 89.52% | 89.36% | 3.04% | 42.91% | 1315 / 54919 | 1785 / 0 |

Remote terrain is the complement of all train/heldout building boxes expanded by the common separation guard. It is never used as Conyberry training negatives. Counts there are an unannotated-background proxy, not verified semantic false positives: missing walls, fences, roads, and props have not been independently classified. Heldout background false positives are measured only where the accepted band objective labels class 0. The band objective can reward thick appearance responses and penalize legitimate LOS placement offsets, so downstream centerline and geometric review remains essential.

## Reproduce and artifacts

Run `/private/tmp/auto-wall-parity-env/bin/python prototype/building_holdout.py` from the private worktree. The script includes assertions for split-window separation, positive samples, model training, and vote class identity. The completed run passed these assertions.

All private assets and results remain in `/private/tmp/auto-wall-building-holdout`: `split.json`, `train-mask.png`, `heldout-mask.png`, `unannotated-terrain-mask.png`, and `scores.json`. Each of `baseline/` and `context/` contains `model.xml`, quarter-resolution `classes.png` (0 background, 1 wall band, 2 door band), `probability-1.png`, `probability-2.png`, `provenance.json`, and `overlay.jpg`. Probability PNGs encode vote fractions ×255; they are not calibrated probabilities. Overlays outline training regions cyan and heldout regions magenta; predictions are green walls and orange doors. Class maps predict globally; only the explicit heldout mask contributes to reported validation metrics.

No extra parameter search, paid models, model downloads, semantic negative annotation, or independent-map validation was performed.


## Fixed hard-negative refinement

The frozen split, 208-source-pixel exclusion around heldout boxes, 31 features, 65 trees, depth 18 and threshold 0.55 remain unchanged. Positives still come only from permitted training building groups and the prior maps. Conyberry background eligibility now covers every pixel outside the heldout guard whose accepted complete-reference band label is class 0 (367,425 pixels); uncertain shoulders and wall/door overlaps are excluded. The receptive-window separation assertion also covers these new negatives.

One predeclared mining pass takes 8,000 permitted pixels with highest baseline nonbackground vote fraction and 8,000 uniformly sampled distinct permitted negatives. Baseline thresholded false positives numbered only 5,086, so the highest-confidence set also includes subthreshold confusing negatives (minimum nonbackground vote 0.446). Class sample counts remain unchanged. No heldout threshold tuning or mining selection occurs. Inference runs through an image/model-only function, and the emitted class map predicts all pixels globally with values 0/1/2.

Permitted-background wall/door false positives fall **5,086 → 901 (82.3%)**. Remote terrain wall responses fall 1,658 → 0, but this terrain now overlaps the permitted training population and is explicitly a training diagnostic. On heldout buildings, wall-band recall falls 89.24% → 76.35%, with precision 89.73% → 90.52%; door recall rises 3.68% → 27.83%, while precision falls 49.47% → 36.39%. Heldout class-0 pixels predicted wall/door increase 1,256 → 2,708 of 54,919. Global wall pixels fall 53,086 → 37,430, while door pixels rise 3,641 → 11,459. This is a tradeoff, not demonstrated geometric improvement: removing scenery wall responses partly shifts errors into doors.

Artifacts are in `hard-negative/` under the same private output directory, with `classes.png`, vote PNGs, `model.xml`, partition-aware `overlay.jpg`, `provenance.json`, `permitted-background-mask.png` and `mined-negatives-mask.png`. Run with `prototype/building_holdout.py hard-negative`. The original split SHA-256 remains unchanged. The baseline remains preserved for comparison.


## One class-balanced follow-up

The original pooled samples are 48,000 background, 27,259 wall, and 4,721 door, so a three-class output head did not imply balanced supervision. One fixed follow-up retained precisely the hard-negative training sample pool and deterministically oversampled each minority class with replacement to 48,000 examples per class. Features, tree settings, split, guard, inference threshold, and all labels stayed fixed. This was the only class-balance variant; results were retained even though poor.

| Variant | Wall recall | Wall precision | Door recall | Door precision | Heldout background FP | Permitted training background FP |
|---|---:|---:|---:|---:|---:|---:|
| Original baseline | 89.24% | 89.73% | 3.68% | 49.47% | 1,256 | 5,086 |
| Hard negatives | 76.35% | 90.52% | 27.83% | 36.39% | 2,708 | 901 |
| Hard negatives + equal class counts | 77.52% | 92.24% | 53.25% | 13.16% | 13,876 | 9,992 |

Balanced training raises door recall but produces too many false doors to be useful. Its global prediction has 36,592 wall pixels and 50,571 door pixels; the terrain diagnostic contains one wall pixel and 590 door pixels. This rejects equal-count oversampling as a useful improvement in this bounded experiment. The wall/door band labels, local appearance features, and class confusion still need substantive work; none of these model variants supports a claim of usable door recovery.

Balanced artifacts are in `hard-negative-balanced/`, with the same filenames as the unbalanced refinement. Reproduce with `prototype/building_holdout.py hard-negative-balanced`. Both completed refinements passed receptive-window separation, class identity, frozen-split integrity, and training assertions; the balanced run additionally asserted equal final class counts. No further mining passes or parameter sweeps were performed. The baseline, context, hard-negative, and balanced runs remain available for downstream centerline review; raster-band precision/recall must not be described as UVTT geometry accuracy.
