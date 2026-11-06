# Throwaway detection experiment

Question: can simple CPU-only image processing produce useful simplified walls and conservative lights on the user's three map styles?

This is a disposable comparison, not the final Rust crate or CLI. No automatic doors, calibrated lights, learned model, or ground-truth-assisted detection. Input reference geometry is used only by the evaluator after detection.

```sh
cargo build --release --manifest-path prototype/Cargo.toml
python3 prototype/run.py
open /private/tmp/auto-wall-detection-review/review.html
```

The runner currently uses macOS `sips`, `/usr/bin/time -l`, and `sysctl` for local evaluation. It expects the three privately supplied UVTT files in Downloads. Neither the files nor their extracted images/geometry are included in this branch. The review HTML embeds thumbnails locally; do not publish it without asset permission.

Candidates: luminance thresholds 40/70, Canny 30/80 with small closing, and a near-black region mask (threshold 25) with radius-3 closing/opening and stronger area/simplification filtering. All cap the long image dimension at 1600 pixels and transform geometry back to original-pixel space. Candidate masks are image-only; grid size is used only to normalize comparison tolerances, not to recover reference walls. The warm-color light heuristic is shared across candidates and intentionally exploratory.

The local review page switches maps/modes and toggles detected walls, reference/object geometry, lights, and random visibility disagreements. Timing covers resize, masks, contours, simplification, and lights; decoding is separate. Process peak RSS includes decoding. Each candidate runs in three fresh processes with warm filesystem cache. These samples are exploratory medians, not a p95, throughput, Linux, or server-capacity claim.

Agreement scores are not verified accuracy: thick-wall tracing conventions differ; the tavern uses object geometry; supplied lights may be invisible gameplay sources. Random visibility probes are diagnostics, not human-reviewed acceptance tests. Reference light matching is greedy one-to-one within 0.5 grid; wall agreement samples length within 0.2 grid. Numeric production gates remain pending human review.

Controlled cases: blank image, a simple closed dark room, and a warm point with white clutter. The runner records their raw detections alongside real-map results. These sanity checks are not a representative validation corpus.

## Optional upstream comparison prerequisites

The current runner includes two Python/OpenCV baselines. They are experimental evaluation tools, not dependencies of the planned Rust library. Prepare them before rerunning:

```sh
git clone https://github.com/ThreeHats/auto-wall.git /private/tmp/auto-wall-upstream-scout
git -C /private/tmp/auto-wall-upstream-scout checkout c11b8fa7ad5923d742722a063b3d4385f68527d8
python3 -m venv /private/tmp/auto-wall-upstream-env
/private/tmp/auto-wall-upstream-env/bin/pip install opencv-python-headless==5.0.0.93 numpy==2.5.4
```

Upstream detector imports run without GUI/manual refinement or its full exporter. Initial GUI slider settings are not the separate named Default preset. Both upstream comparisons use fixed-pixel simplification to isolate detector differences. See FINDINGS.md for versions and limitations.

## Current milestone

Auto-Wall parity first: see [PARITY.md](PARITY.md). Full automatic-path captures and a stage comparator now provide the baseline for a faithful Rust port. The old candidate modes are retained only for historical comparison. To attach local full-path captures to the review page, run `python3 prototype/add_parity_review.py` after producing them under `/private/tmp/auto-wall-parity/`.

## AI annotation comparison

See [AI-EXPERIMENT.md](AI-EXPERIMENT.md) for the four-pass visual wall exercise and local rebuild instructions. This remains separate from the Rust parity work.
