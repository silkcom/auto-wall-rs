# Building shape rules on two maps

Date: 2026-11-07. Throwaway experiment in `prototype/building_shapes.py`; not a production detector. The user requested building/room shape evidence instead of memorized map colors. Existing learned appearance models and organic-model preferences are unchanged.

## Implemented cues

The pipeline converts the image to grayscale, uses local contrast normalization and detects straight segments with OpenCV LSD. It does not train or load a color classifier. The same rules and size hint are applied to Conyberry and the supplied different-map image.

- Nearby parallel faces suggest wall centerlines. Face width and segment lengths are expressed relative to the size hint, not fixed map coordinates.
- Long unpaired edges can help discover enclosures when only one wall face is visible. They are not automatically exported as walls.
- Line fragments are grouped into closed-shape hypotheses with building-sized area/width, limited aspect ratio, corner/axis consistency, and support on several sides. Short gaps are permitted only at the proposal stage.
- Aligned patterns well inside a region support a floor/roof-like interpretation. The interior inset excludes the wall/fence perimeter itself.
- Exported green fragments still require paired-face evidence near a retained shape. Unsupported closure edges are not filled in as permanent blockers. Orange gaps are unverified opening proposals, not recognized doors.

These are rough priors. This is not yet the requested room-and-door graph. Roof-only behavior and lights are not implemented/validated. Smooth interiors, curved walls, clutter, props, eaves and open structures remain difficult. Absence of a building proposal does not prove a feature is nonblocking.

## Checks that changed the rules

Early strict enclosure detection produced almost no regions because doors/windows break line evidence. Proposal grouping therefore allows shorter observed fragments and virtual gaps while retaining separate rules for exported walls. A synthetic rotated-room test exposed a morphology border artifact; zero padding fixed it globally.

A closed fence with identical ground inside/outside initially passed because its inner edge was counted as interior texture. The revised inset rejects that example while retaining a patterned room and its inverted-lighting/rotated versions. The passed open/closed fence cases are synthetic checks, not a claim that all real fences are classified correctly.

Working resolution is normalized to 32 pixels per size-hint unit with a 2800 pixel cap. A single coarse-scale check was also applied to both maps; it did not yield a usable wall graph and was not promoted. No per-image palette choices or manually supplied wall coordinates are used. No second-map annotations or training labels were added. Both images were inspected during development; this is a two-map qualitative experiment, not a pristine blind benchmark.

## Final measured result

Final saved runs use identical code hash, rule dictionary and size hint 49.0002073 on both images. That hint comes from Conyberry; the other map's actual grid remains unknown.

| Image | Retained shape hypotheses | Supported wall fragments | Unverified openings | CPU time |
|---|---:|---:|---:|---:|
|Conyberry|3|24|11|35.49s|
|Different map|10|86|22|1.75s|

Counts do not mean correctly recognized rooms/buildings. Some hypotheses are furniture or other structures. The unoptimized Python grouping is especially slow on Conyberry's dense line field.

On the existing Conyberry spatial development subset at 0.2 grid tolerance, exported wall precision is 47.13% and recall 1.62%; no held-out portals match. This is much worse than the learned hard-negative wall result. The rules are therefore NOT a replacement for that candidate.

On the other image, visual inspection shows partial real exterior walls where the learned appearance models previously missed almost everything. Walls and internal partitions are still incomplete, and furniture edges remain. No ground-truth geometry exists there, so no correctness percentage is reported.

## Review and conclusion

Both maps now have `Structural shapes · grayscale proposals`. Yellow closed outlines are unverified hypotheses; green lines are supported fragments; orange spans are unverified openings. The shape layer has its own toggle and never uses reference magenta/cyan. Conyberry keeps the user's preferred hard-negative candidate as default.

The experiment supports using geometric/contextual evidence as a proposal layer across differing appearances. Hard shape gates are too restrictive for usable wall recovery, and geometry alone still confuses rooms with objects. Reliable region grouping, wall completion and door semantics remain unresolved. Do not claim accepted quality or generalization from these outputs.

Run with the existing OpenCV/NumPy environment:

```
python prototype/building_shapes.py IMAGE OUTPUT --grid SIZE_HINT
python prototype/building_shapes.py --selfcheck
```

Checks cover contrast inversion, rotation, deterministic replay, blank input, and open/closed nonblocking-fence examples. All inference is local CV: no learned model, paid vision calls or per-map token charges. Development-agent usage and local CPU are separate from that statement. Images, geometry, diagnostic masks and manifests remain private outside git.
