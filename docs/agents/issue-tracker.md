# Issue tracker: GitHub

Issues and specs live at https://github.com/silkcom/auto-wall-rs/issues.

Use `gh-axi` for supported GitHub operations; use `gh` for operations
the wrapper does not support. Specify `--repo silkcom/auto-wall-rs`
when the repository cannot be inferred from origin.

- Publishing to the issue tracker means creating a GitHub issue.
- Fetching a ticket means reading its body, labels, and comments.
- For multiline bodies, write the text to a temporary file and use
  `--body-file`.

## Pull requests as a triage surface

PRs as a request surface: no.

## Wayfinding operations

- Map: an issue labeled `wayfinder:map`; decisions are indexed by named links.
- Tickets: native sub-issues, labeled `wayfinder:research`, `wayfinder:prototype`,
  `wayfinder:grilling`, or `wayfinder:task`. Use `gh-axi issue subissue`.
- Blocking: native GitHub issue dependencies. Use `gh api --method POST
  repos/silkcom/auto-wall-rs/issues/<child>/dependencies/blocked_by -F
  issue_id=<blocker-database-id>`. Fetch the database ID through the issues API.
- Frontier: open, unassigned children with no open blockers, in sub-issue order.
- Claim: assign the ticket to the driving developer before investigation.
- Resolve: post a resolution comment, close the ticket, and append a named link
  with a one-line gist to the map's Decisions so far.
