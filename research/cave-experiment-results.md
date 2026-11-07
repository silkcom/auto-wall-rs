# Cave algorithm experiments — 2026-11-06

These throwaway prototypes investigate raster-only cave reconstruction. They are not the Rust product. Authoritative geometry is used for development/evaluation, never supplied to inference. User images, reference vectors, trained models and rendered reviews remain private outside the repository.

## Working quality measurements

Length-weighted boundary precision AND recall within 0.1, 0.2 and 0.3 grid squares; sample visibility disagreement separately. These are provisional measurements, not an agreed definition of “98%.” Reference-against-itself yields precision/recall 1 and zero sightline disagreements; empty and translated controls fail. Open object paths are scored separately from closed structural boundaries.

Within-map spatial splits do not demonstrate new-map performance. Repeated development scoring is validation, not a pristine test. A separate paired frost-cave raster was inferred with frozen models before its geometry was read; hashes record that ordering.

## Measured results

At 0.2 grid tolerance:

| Method | Development cave P / R | Independent frost cave P / R |
|---|---:|---:|
| Multiscale material random forest | 92.90% / 81.73% | 0 recall |
| Same RF + four local ICM passes | 87.37% / 87.39% | not tested |
| Boundary RF + four ICM passes | 86.76% / 90.53% | 0 recall |
| Boundary-sampled RF | 91.56% / 85.75% | 0 recall |
| Quantile-normalized RF | 92.25% / 82.33% | 0% / 0% |
| Tiny CNN, selected training step750 | 85.70% / 63.50% | 54.20% / 60.12% |
| AI semantic seeds + four GrabCut passes, corrected convention | 72.00% / 40.32% | 100% / 100% |

The frost semantic result is promising on a simpler visual style, not a general-quality claim: at 0.1 grid its P/R are 96.17% / 96.24%. Of 2,000 sightline probes it falsely opens16/728 reference-blocked rays and falsely blocks12/1272 reference-open rays. The same pipeline fails badly on the more textured development cave. A third image has no reference geometry and can only support visual inspection.

## Refinement findings

- Authored LOS convention includes some visible wall faces/shadows before the opaque core. “Walkable floor vs all rock” is the wrong semantic labeling prompt.
- Correcting that convention helps the original semantic candidate but is not enough. Globally pooling sparse color/material labels can swallow tunnels or expose solid rock.
- Generic MobileSAM masks can agree with semantic seeds while missing intended cave boundaries. Crop fusion introduced artificial seams; reject it.
- Local shortest-path/geodesic propagation has 100% seed agreement yet leaks through weak boundaries and draws arbitrary room splits. Reject it.
- The CNN starts overfitting one-map training after the selected step750; longer training is not a solution to missing map/style diversity.
- Combining boundary-focused training with the same four ICM passes reduces development sightline errors from187 to149, but trades precision for recall and still collapses on new styles. Reject for general deployment.
- Four deterministic solver iterations are cheap. Repeating an incorrect semantic model does not produce correctness; the reference test must measure tunnel and island preservation.

## AI labeling cost

User-provided SOL rates: uncached input $2/M, cached input $0.10/M, cache writes $2.50/M, output $10/M. Output includes reasoning; do not add it again. No separate cache-write tokens were reported.

| Map / label rounds | Uncached input | Cached input | Output | Observed cost |
|---|---:|---:|---:|---:|
| Development cave / 3 | 39,064 | 267,392 | 1,753 | $0.1223972 |
| Unpaired textured cave / 3 | 43,501 | 262,400 | 1,882 | $0.1320620 |
| Independent frost cave / 1 | 4,124 | 142,976 | 627 | $0.0288156 |

These cover isolated label-agent tasks, including repeated context. They exclude research, integration, evaluator development and local CPU. The frost labeling task inherited a warm context; pricing all147,100 input tokens as uncached instead would be $0.30047, not a measured cold production request. Neither cost nor one successful map establishes deployable accuracy.

## Next evidence needed

The quality bottleneck is semantic boundary identification across map styles. A representative, legally usable paired training/validation corpus and map-level splits are more informative than further freehand coordinate passes or one-map model fitting. Preserve the original Auto-Wall parity experiment as a baseline, while investigating the user's newer reusable-algorithm objective.

## User review follow-up

User selected unseen textured cave Semantic round2 as clearly best. Keep it as the preferred visual baseline; round3 is a regression, not a successor. Preferred methods now initialize per map, with an optional map-index URL query for direct review.

Four topology-preserving local passes changed1,590 quarter-resolution pixels (about0.2% of map), kept every seed and floor/solid component count, and took0.68seconds. Native-ish source crops show small alignment shifts only: missing barriers and furniture blockers remain. This compare-only result is not established better.

A further32 uncertainty/coverage/confidence-audit samples retained round2 labels and added image-only feedback. Global retraining produced gross false room cuts and missing floor; balanced-class retraining partly restored floor but still failed. Reject both outputs and keep round2 unchanged. Class frequency in the audit sample policy is not a true image prior. Future corrections need local scope and explicit preservation checks before promotion.

Additional unseen label task:145,747 input tokens,107,648 cached,38,099 uncached,451output; $0.0914728 at user rates. All four label rounds total$0.2235348, including rejected experiments; preferred round2 alone remains$0.080108. Local cleanup itself used no further vision-label call.

## Shared foundation and portfolio follow-up

User accepts Frost semanticround1, unseen semanticround2/local cleanup, and canonical Boundary+ICM as closest but artifacty. A portfolio of5–10candidates with user selection is now an acceptable product direction; automatic method ranking is not required to investigate that option. Candidate generation must still be image-only. Share semantic observations and image features across candidates instead of multiplying paid calls.

One shared RF trained across the three development styles (reference labels for canonical/Frost, explicitly accepted AI-mask pseudolabels for textured cave) avoids style collapse with identical4ICMpasses. Canonical P88.25/R85.02at0.2grid,124false-open/56false-blocked; Frost P99.86/R99.77at0.2grid,15false-open/13false-blocked. Textured cave visually reproduces the accepted contours. These are training reproduction scores, not generalization evidence. Canonical remains worse than its preferred specialist. Inference reads only image+model and uses no paid vision call; the model's training includes AI-derived pseudolabels. CPU21.18s canonical,1.95s Frost,17.98s textured on the measured machine.

Fixed-unary semantic ICM ablation does not solve perception: canonical P41.49/R33.82at0.2grid; Frost P98.06/R97.98, worse than accepted GrabCut output. Unseen grows small false contours around bridge/furniture. Preserve current preferences.

Conservative paired-wall-gap door probe:0proposals for8Buildingreferenceportals;1unmatchedTavernproposal for12portals, visually a chair. Reject. Current binary cave contours do not provide door semantics or movable portal identity. Need semantic door proposals anchored to structural walls; closed doors cannot be inferred only from gaps.

The review now includes4map cases and explicitly labels each candidate: localCV, localML(no paid vision call), paid vision labels+local processing, or reused paid labels(no additional call). Shared-model candidates identify their training-map limitation. No additional paid label task was needed for this shared-model/door/solver batch; research/development AI usage is outside the per-map label cost table.

## Organic/building split and full-resolution Conyberry test

User now prefers Shared model+ICM on ALLthree caves; review defaults reflect that. Treat it as the organic specialist. A separate building specialist is a sensible hypothesis because structural building LOS is a thin/open centerline graph with portal spans, not a floor/solid-region perimeter. Mixed scenes may ultimately need both specialists locally rather than whole-image routing.

Explicit building contract: emit ONEline midway between the two visible wall faces. Intersections join centerlines. Door spans attach to this graph, and permanent wall edges must be removed across openings. This geometry stage does not repair missed wall perception; no usable building centerline exporter is established yet.

Located the full Conyberry source4054×2846; its .thumb counterpart is only a200×200crop. Both experiments use the full source and exclude it from training. No Conyberry reference geometry or training annotations were used. Organic inference5.80s,99.67%open, misses buildings. New dedicated3class buildingRF trained only on the prior Building/Tavern labels, with23appearance+8directional features, also fails blind Conyberry: most walls missed, portal false positives on terrain. Inference6.00s. These are qualitative failures, not numeric accuracy scores.

The building-classifier preview is shown as a failed raster overlay in the review, explicitly NOT UVTT walls/doors. No centerlines were fabricated from unreliable predictions. Green=predictedwallband;orange=predictedportalband on that preview, with no reference overlay. Existing gap probe emits0Conyberryproposals. All these inference paths are local and require no paid vision calls; development agent usage is separate.

Representing wall/portal classes is feasible; generalization from two maps remains inadequate. Potential causes include art style, apparent building scale, resolution and annotation-to-material mismatch; no ablation establishes which dominates. Need broader building supervision and per-building/native-resolution evaluation before tuning a final model or promising reliable doors.

## Existing hand-drawn Conyberry reference discovered

The user supplied an existing local game with manually authored Conyberry geometry AFTER the frozen model predictions. Read-only retrieval saved geometry/map fields only, excluding campaign, creature, account and log data. The editor marks its source manual_graph. It contains396structural wall segments in205paths,128typeddoor/portal spans,479anchors,0objectpaths and0lights. All saved portals are closed. No server edits or training were performed.

Source map URL matches the full4054×2846Conyberry raster. Bag's renderer maps each geometry unit to52world pixels; saved image zoom1.06122andzero offsets imply49.0002073source pixels/unit. Full-map overlay inspection confirms alignment across widely separated buildings. Generic evaluation-only converter bag_reference.py explicitly rejects nonzero offsets or active layers until those transforms are verified. Reference-self/empty/shifted scorer controls pass.

The review now shows genuine magenta structural reference and cyan portal reference on Conyberry, separately from green/orange classifier predictions. The frozen organic candidate scores0precision/0recall at0.1–0.3grid and falsely opens all662sampled reference-blocked structural rays. This confirms domain failure. The building classifier still emits raster bands only, so no fabricated centerline/portal accuracy is reported. Neither model has trained on this newly obtained reference.

User identifies fences with grass/gravel on both sides as important nonblocking hard negatives. Building detection must learn VISIBILITYblocking semantics, not every dark edge or wooden boundary. Use contextual floor/terrain/room/junction evidence; grass on both sides alone is not a universal rule for fence height or opacity. Score false blockers on fences/roads separately from missed structural walls and door/portal identity. Future Conyberry training must use explicit whole-building/guarded spatial splits and label results accordingly, or preserve the full map as a blind test.
