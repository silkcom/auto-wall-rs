# Cave raster + geometry corpus: actionable sources

Researched 2026-11-06. Scope: distinct new cave layouts, free/no account/no model downloads, small fixtures. No public fixture was downloaded in this pass; do not mistake the candidate list for an acquired or verified corpus. Code licenses below are not assumed to license map artwork.

## Recommendation

Use **Watabou-generated cave SVG plus its matching PNG** as the first additional corpus, and obtain independent artist-authored held-out pairs before claiming 98% quality on unseen maps. Generated pairs supply exact rendering geometry, but neither synthetic geometry nor several styles of the same geometry demonstrate generalization to Carlos-style textured authored maps. Split by seed/layout and by generator/style family; never split one map into train/test crops.

### 1. Watabou Cave/Glade: strongest immediately usable generated-pair avenue

- [Author's official page](https://watabou.itch.io/cave-generator) explicitly permits copying, modifying and commercial use of generated maps, with attribution optional. This is **output permission**, independent of code licensing. The author states current source is not shared; avoid treating deployed JS as open-source training infrastructure.
- [Live generator](https://watabou.github.io/cave-generator/) runs without a purchase/account. Its first-party live page and deployed [Cave.js](https://watabou.github.io/cave-generator/Cave.js) were fetched successfully. The deployed menu contains both PNG and SVG export functions. Both derive their export framing from the current model rectangle plus the same padding; retain both original files and verify raster/vector transforms.
- Concrete small acquisition batch: generate three separate **small** maps: `tree + entrance + dry`, `connected + passage + wet`, and `hub + junction + dry`. Save a fresh seed/layout each time as SVG and PNG before pressing Enter. These are suggested parameter combinations, **not acquired files or verified stable seed URLs**. Include a narrow-tunnel example and a rock-island/loop example, because a mistaken bridge can cause massive visibility failures. For each layout retain at least one alternate palette as a rendering variant, not an independent topology sample.
- Crucial geometry evidence: [EnderPy's importer](https://github.com/EnderPy/one-page-importer) documents matching cave PNG+SVG exports and cave fog import. Its [actual parser](https://github.com/EnderPy/one-page-importer/blob/main/src/SVGImport.ts) finds the SVG path whose fill is `#FF0000`, handles M/L/C commands, and applies group transform plus SVG dimensions. That strongly suggests an authoring-geometry path, rather than a learned raster detector. **Do not copy its simplification defaults as ground truth**: retain every source contour, correctly close paths, flatten curves under a pixel-error budget, and validate all nested transforms and holes. The parser's first-colored-path/first-transform assumptions are fragile.
- [Cartomancer](https://github.com/DimitroffVodka/cartomancer) independently supports Cave/Glade walls. Its [generator guide](https://github.com/DimitroffVodka/cartomancer/blob/main/docs/generators/cave-glade.md) supplies parameter suggestions, but is internally inconsistent about newer palette/UI support; use the live generator as authority. Do not rely on its bundled third-party generator source licensing.
- Ground-truth class: **exact generated SVG boundary before conversion**, then a candidate UVTT reference after coordinate/closure/visibility checks. Not independently human-authored UVTT. A path-to-UVTT converter is required. Cost is local processing, not API inference.

### 2. Delvework Sampler: genuinely paired cavern UVTT, narrower rights

[Official sampler page](https://cabincircuit.itch.io/delvework-sampler) offers `Delvework-Sampler.zip` (7.2 MB), containing **The Hollow Deeps** frost cavern plus **The Weeping Crypt** and **The Cinder Sanctum** (manmade dungeons). Each map is 30×40 squares with player PNGs at 2100×2800 and authored/exported `.dd2vtt` walls/doors. Both editions are included; edition variants are not new layouts. The author says layouts and textures are procedural, not hand-painted.

License permits personal games, streams, and inclusion in published adventures, but expressly prohibits redistributing map files. This is **not an open training-data license**, and training permission is not stated. Useful lead for a private held-out functional benchmark only after clarifying permissible use; do not put files into a distributable corpus or infer blanket permission from “free.” No download was made. The itch Download Now flow is the concrete acquisition point; no paid pack is needed. UVTT quality and cave topology have not been inspected, so treat walls as reference candidates, not proven ideal geometry.

### 3. Tabletop Generators: permissive output and SVG, access unverified

[First-party Cave Map Generator](https://www.tabletopgenerators.com/cave-map-generator) advertises SVG/PNG and says its maps are entirely drawn by its own code with no third-party art. It permits games, streams, zines, and published modules, optional credit. Its documented generation retains the largest connected cave and supports pillars, chambers and passages. This is another potentially distinct visual family.

However, direct Python fetch returned **403** and web open failed; only first-party search-index content was available. No map was acquired, no SVG interior path was inspected, and no geometry export beyond rendered SVG was established. Keep as an acquisition lead, not a verified exact-GT corpus. Do not bypass access controls.

## Sources rejected as immediate corpus

- [AlexeyDomozhirov/Caves-generator](https://github.com/AlexeyDomozhirov/Caves-generator): MIT software with downloadable example PNGs (`small-caves-system.png`, `big-caves-system.png`) and settings. [Renderer source](https://github.com/AlexeyDomozhirov/Caves-generator/blob/master/src/CavesSystem/Draw/Func.hs) renders Alive/Dead cells as console characters. It could expose a binary grid for owned procedural fixtures after adaptation, but existing example pictures are console screenshots, not high-quality raster+UVTT pairs. MIT software is not enough reason to call screenshot art training-licensed.
- Dungeon Map Builder's [official export docs](https://www.dungeonmapbuilder.com/docs/export) confirm PNG+UVTT 0.3, walls from cell-grid room geometry, door gaps and physical-object LOS. This is authoring geometry, **not evidence of an automatic detector solving arbitrary cave rasters**. No independently licensed cave examples or verified organic contour output were found; do not count it as a new cave benchmark.
- Existing Carlos Pro Maps Lesser Caverns file remains one private paired authored-map family. Crops, recolors, and resampling cannot raise the independent layout count. No private archive was extracted or asset uploaded.

## Minimum next experiment

Acquire 3–6 Watabou SVG+PNG pairs, preserve output-permission page and generation settings, hash every file, and derive a lossless floor mask/reference contour from SVG. Validate by raster overlay and ray-visibility agreement, including loops, holes, entrances and narrow passages. Use these to test topology and coordinate conversion. Separately secure at least several textured artist-authored pairs in different visual families for untouched evaluation. No source here supports a defensible 98% across-new-map claim by itself.

## Follow-up acquisition attempt

Tried actual paired-export acquisition in an isolated Chrome session. `chrome-cli` is absent. CUA `createBrowserTab("chrome", ..., {sessionName:"🪨 Cave corpus"})` failed with **browser access host is unavailable**; native `getApp("Google Chrome")` also failed with server timeout `-10005`. No generator UI was reached and no map pair was downloaded. Fallback GitHub recursive trees for EnderPy/one-page-importer and DimitroffVodka/cartomancer contained no cave SVG/UVTT fixtures; importer docs contain PNG screenshot previews only. These are not promoted to reference pairs. Corpus-public therefore remains empty; the missing acquisition is explicit, not silently replaced with invented geometry.


## Acquired private inference benchmark (follow-up)

Downloaded official free `Delvework-Sampler.zip` via its no-thanks/free download endpoint (7,651,337 bytes), without login/payment. Extracted only Hollow Deeps files plus README/license to `/private/tmp/auto-wall-algorithm/corpus-private-frost`. Actual sampler contains JPEG variants at 70px/grid, not PNG variants as the marketing description suggested. Extracted the embedded PNG from the 50px/grid UVTT to create an exactly paired inference raster `18-Hollow-Deeps_uvtt-image.png` (1500×2000; map30×40, origin0, pixels_per_grid50). `provenance.json` preserves source, purpose, SHA256 hashes, and resolution metadata. The LOS/portal geometry was not inspected; predictions must be frozen before parent evaluation. This is PRIVATE INFERENCE BENCHMARK ONLY: no training and no redistribution. The terms permit private game use and maps within published/streamed works; they do not expressly grant training rights. Original license is preserved. The downloaded archive remains private at `/private/tmp/Delvework-Sampler-private.zip`.
