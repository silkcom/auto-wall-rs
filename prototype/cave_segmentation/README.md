# Throwaway cave segmentation candidate

Question: can low-cost raster-only classical CV reproduce authoritative cave LOS geometry on unseen maps?

Run with Python + OpenCV + NumPy:

```
python candidate.py train IMAGE MODEL.xml OUTPUT_DIRECTORY --reference DEVELOPMENT_MAP.dd2vtt
python candidate.py infer NEW_IMAGE MODEL.xml OUTPUT_DIRECTORY
```

The inference command has no reference argument. `infer()` calls only image feature extraction, an OpenCV random forest, morphology, component filtering and contour approximation. Features are normalized LAB, local channel means/deviations at 3/9/25 working pixels, grayscale and gradient magnitude. The serialized model contains forest thresholds and learned class votes, no coordinate arrays, per-map seeds or distance fields. Original raster pixels are reduced by four; feature extraction never uses x/y coordinates. Each returned `walls` item is `[x1,y1,x2,y2]` in original image pixels.

Training assumptions: closed LOS paths are filled using even-odd parity to infer floor and solid regions. Paths must explicitly repeat their starting point; open paths are never implicitly closed. This development reference has 37 closed LOS paths and 15 open object LOS paths. Open-object paths cannot establish which side is solid, so a 36-pixel band around them is excluded from both training and heldout segmentation scores. A 12-pixel closed-boundary band is excluded from training samples. This is a pragmatic labeling assumption, not a general UVTT semantic guarantee. The train output contains labels and a spatial-holdout mask; the private experiment folder also contains an overlay of labels over source.

Spatial split: 512-original-pixel square tiles, deterministic `(tile_x + 2*tile_y) % 4 == 0` held out, with 64-pixel guards on every tile edge. Largest feature radius is 48 original pixels, so feature receptive fields cannot cross between retained train and heldout samples. Up to 40,000 sampled pixels per class; 65 trees, max depth18, min leaf12; fixed RNG seed42. Heldout testing is within the same map; it does NOT establish independent-map generalization. Full-image walls also include areas used in training and must not be described as an independent test.

Deterministic inference refinement: close5x5 then open3x3; remove positive components smaller than120 working pixels; remove contours smaller than80 pixels area; polygon approximation1.5 working pixels. Contours at image clipping edges are omitted because raster frame itself is not evidence of a wall. Thin open LOS features are an acknowledged weakness: segmentation naturally produces closed boundaries. No manual map coordinates or hand repair.

Private development assets live outside this subtree under `/private/tmp/auto-wall-algorithm/`: learned model, train/labels-overlay.jpg, train/training-labels.png, train/heldout-tiles.png, training metrics, result/overlay.jpg, raw and refined masks, walls JSON, runtime/provenance JSON, and blank control. These assets must not be published as generic model validation.

Cost: no network or paid model/API; CPU only. Local timing supports cheap execution, but no hosted dollar estimate is established. This candidate cannot claim the requested ~98% geometry quality. Its purpose is to measure the classical baseline and reveal failures, not hide them with cosmetic fixes.

A user-supplied Bag of Mapping geometry snapshot can be converted for evaluation with `python bag_reference.py snapshot.json map.jpg reference.dd2vtt`. The snapshot needs only mapZoom/mapXOffset/mapYOffset/vttData and optional editor metadata/layer fields. The default base world width is52; only verified zero-offset, unlayered maps are supported. Reference data remains separate from inference and is never committed.
