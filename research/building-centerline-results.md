# Building centerlines and held-out groups — 2026-11-06

Question: can a local building specialist learn the accepted hand-drawn Conyberry visibility geometry without memorizing every building? This is a disposable prototype; no Rust product implementation or reliable automatic doors are established.

## Frozen data split

The accepted reference supplies396wall segments and128door/portal spans. Raster connectivity includes portal spans, joins endpoints within4source pixels, and merges overlapping/nested graph boxes to a fixed point. Alternating box-center x-order partitions14groups into7training/7heldout. Some groups are detached structures rather than complete buildings. Training excludes a208source-pixel buffer around held-out regions; feature support is at most104source pixels. The two earlier building maps remain training sources. No x/y features or map-identity routing are used at inference.

These are repeatedly inspected SAME-MAP SPATIAL DEVELOPMENT results, not independent map/artist validation. The reference and split are private. The initial blind model remains archived separately.

## Centerline representation

`building_centerlines.py` thins predicted structural material with Zhang–Suen, traces an eight-connected pixel graph without diagonal right-angle shortcuts, and simplifies paths by0.5working pixels. Source coordinates use actual image/mask dimension ratios, including pixel-center placement, rather than assuming divisible-by-four sizes. This emits single centerlines, not contours around both material faces. Junctions share endpoints; closed rooms remain single rings. A one-pixel predicted portal clearance prevents permanent wall pixels from remaining across proposed door regions.

Portal bands become PCA-axis span proposals. `building_portal_support.py` can require both ends to attach to compatible structural terminals, reject crossing/overlapping permanent blockers and deduplicate spans. This is geometric support, not door recognition. Unsupported portal guesses are not accepted as doors. Because the predicted material can itself be wrong, there is no blanket claim that these graphs preserve real map topology.

## Measured geometry

At0.2grid=9.80004source pixels, length-weighted held-out wall centerline agreement:

| Variant | Precision | Recall | False-open structural probes | False-blocked structural probes |
|---|---:|---:|---:|---:|
|31feature RF baseline|66.20%|91.99%|27/403|21/119|
|Hard-negative training|71.86%|88.64%|52/403|12/119|
|Hard negatives + equal class totals|76.59%|87.35%|57/403|7/119|

Structural probes treat portal spans as open; all-closed portal scenarios are recorded separately. Full-image geometry contains trained-on regions and is not the primary comparison. UI now defaults these methods to held-out boundary AND held-out visibility scores.

The baseline preserves more barriers; precision-oriented variants reduce extra blockers but introduce more leaks. No single variant wins all criteria. None is production quality. The review initially selects the baseline for coverage; users can compare all three.

Band segmentation scores (roughly89%P/R for baseline walls) are NOT these geometric scores. They should not be presented as UVTT accuracy.

## Door failures

The RF baseline matches0of75held-out portal instances using both corresponding endpoints within0.2grid. The hard-negative portal support check retains no held-out proposals. The balanced model retains1held-out proposal, which is wrong. Doors remain unsolved; do not auto-export those proposals as recognized doors.

A separate learned-wall endpoint-gap proposal pass has weak recall and overwhelming false positives: held-out matches2/75from76proposals on baseline,3/75from96on hard negatives,4/75from74on balanced walls. This also is not a door solution. Raw image-edge gap detection failed earlier.

One fixed1000step small local CNN collapsed toward background. A single causal sampling correction (portal/wall/uniform crop strata, unchanged architecture/loss/steps/split) restores some wall learning but remains weak: held-out wall-band precision34.44%,recall71.94%; still zero portal predictions despite405,831supervised portal-pixel exposures. Preserve the negative results; do not replace RF or interpret them as evidence that contextual models cannot work. See building-context-cnn.md.

## Cost, runtime and verification

All map inference here is LOCAL ML/CV: no paid vision-label calls or token costs per map. Development agent usage is separate and remains charged to the weekly quota cap. Reference labels were supplied by the user, not generated through new paid vision calls.

Single CPU runs including image decode/model load/features/prediction/centerlines and optional portal support, excluding visualization:12.17sbaseline,13.21shard negatives,12.82sbalanced. No p95/concurrency or production Rust performance claim. Wall-gap enumeration is additional work and is not included in those figures.

Image/model-only inference reruns reproduce saved class maps with reference-label helpers replaced by throwing stubs. Checks cover a centered wall, an open doorway, a closed room, blank input, portal endpoint direction/duplicates/shortened spans, permanent-blocker rejection and held-out visibility inclusion/exclusion. Review checks verify held-out scores, portal failure disclosures, portal visibility toggle, and retained accepted cave preferences.

Next bottleneck: reliable semantic doorway/portal instances and stronger contextual separation of structural walls from props/fences/terrain. More threshold changes on these same validation groups are not a substitute for new building-map evidence.
