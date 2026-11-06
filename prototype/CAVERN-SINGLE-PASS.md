# Cavern single correction pass

The user requested exactly one cavern-only correction pass in a fresh-context subagent, prioritizing alignment over wall count, plus measured usage/cost at supplied SOL rates.

The isolated task inspected source crops, prior AI geometry/overlay and screenshot feedback, authored one replacement geometry, then rendered and inspected it once. No source UVTT wall arrays were read. Result: 1,108 wall segments, no doors, and 16 preserved light sources. Coordinate/bounds/duplicate checks passed, but visual placement acceptance failed: boundaries remain misplaced around the middle shelf, crystal peninsula, east passage and lower curled shelf. No additional quality redraw was performed. It is retained as an explicitly failed comparison, not an accepted improvement.

The review page retains AI v2 and adds `Caverns · single pass · placement failed`. Per-map candidate buttons now accommodate a cavern-only candidate without breaking navigation to other maps. Existing portal/light/visibility controls remain usable.

`add_cavern_pass.py` reads the completed isolated session's latest cumulative token counters from a private session manifest, computes cost with Decimal using the user's rates, validates/attaches the local result, and writes token-cost.json/token-cost.md under `/private/tmp/auto-wall-ai-v3/`. It excludes parent coordination and integration. Input/output count the full agent workflow including context rereads and final response; this is not one inference call. Reported cache writes were zero.

Private source-derived geometry, method.py, notes and final overlays remain under `/private/tmp/auto-wall-ai-v3/caverns/`, uncommitted. Rebuild requires those private files and the session manifest: `python3 prototype/add_cavern_pass.py`. No backend/quality acceptance decision changed.
