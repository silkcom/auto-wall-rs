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
