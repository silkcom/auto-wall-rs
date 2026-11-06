# Fresh-context AI map revision

The user rejected the first cavern version because oversimplification allowed sight through walls, supplied a screenshot where pink boundaries were closer to the desired result, and asked for a fresh-context revision with doors, lights and measured tokens per map.

Three separate subagents were started with no parent conversation fork, one per map. Building and tavern received original images; the cavern task also received the feedback screenshot. None read supplied UVTT wall-coordinate arrays. Each task owned a private output directory; the coordinator integrated and reviewed results separately.

| Map | Walls | Doors | Lights | Visual rounds |
| --- | ---: | ---: | ---: | ---: |
| Building | 8 | 1 | 8 | 2 |
| Tavern | 21 | 5 | 17 | 3 |
| Caverns | 1532 | 0 | 16 | 4 |

The cavern revision follows floor-facing cliffs, narrow winding barriers, and individual significant boulders/pillars, rather than merely outlining near-black voids. No visible cavern doors were identified. Quality and preserving sight barriers take priority over minimizing wall count. Exact cliff opacity, small debris and pixel fit remain uncertain.

The tavern agent performed a third round after coordinator review found a barrier spanning the broad stair opening. That span was opened; a separate narrow portal remains. The cabin treats shutter-like features as opaque windows and represents the broad southern entrance as a door. Light positions are visual estimates; range/intensity are documented defaults, not physically recovered values.

## Local review and geometry

`/private/tmp/auto-wall-detection-review/review.html` retains the earlier candidates and adds `AI v2 · fresh context · walls/doors/lights`. Walls are green, doors cyan, and light markers yellow. Original UVTT overlays can be toggled separately. A click-to-test-sight preview uses the authored wall segments and closed portal spans; opening doors removes portal blockers.

Validation: finite/in-bounds coordinates, no zero/duplicate segments, portal geometry, inspected overlays, and browser interaction/console checks. A closed-cabin visibility check stays inside its enclosure; removing its portal blocker opens sight. Coordinator-selected cavern probes block the central boulder and river pillar and preserve the two river entrances. These are spot checks, not an independent topology/accuracy benchmark. A complete leak-free claim is not made.

Private assets live under `/private/tmp/auto-wall-ai-v2/{building,tavern,caverns}/`: agent scripts, per-round overlays, notes, result.json, and no-image ai-v2.uvtt. Images and map-derived geometry have not been committed or uploaded. `add_ai_v2_review.py` validates and scales these original-pixel outputs into the local comparison and UVTT grid units using the known grid calibration.

## Measured token accounting

`token_report.py` reads only the three known experiment rollouts and the coordinator rollout named in a private session-manifest.json. It uses each thread's latest cumulative token_count total, not a sum of cumulative snapshots. Completed map threads include final responses. Cached input is part of input, and reasoning output is not added twice. The per-map report separates input, cached input, uncached input, output and total tokens.

Map-agent totals are separate from coordinator overhead, measured as a parent-counter delta beginning immediately before the feedback request. Coordinator figures are explicitly through a snapshot; subsequent report integration and the final user response are excluded. Fresh-context agents still receive system/tool instructions and reread their growing map-local context between tool calls. Reported tokens cover the iterative Codex workflow, not one-shot image-inference costs. No dollar price or plan-quota conversion is inferred.

Local reports: `/private/tmp/auto-wall-ai-v2/token-usage.md` and token-usage.json. The latter also records per-thread identifiers and source-counter timestamps, so it remains local. Rebuild with `python3 prototype/token_report.py --final` and `python3 prototype/add_ai_v2_review.py`. The private session manifest, baseline counters and result files are required. [Official App Server documentation](https://learn.chatgpt.com/docs/app-server#turn-events) describes per-thread usage notifications.

This side experiment does not replace the Auto-Wall-parity milestone or establish automated model-inference quality, cost or runtime.
