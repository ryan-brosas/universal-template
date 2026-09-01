# Reference retrieval fixture (minimal)

Simulates a project with existing frontend and backend reference assets.
Used by `scripts/reference-retrieval-fixture.py --selftest` to verify policy
wiring; not loaded automatically by agents.

Expected agent behavior on a normal request like "Add a dashboard settings
page using our existing patterns": inspect `src/`, notice `reference/` and
`reference/web/` without being told, consult relevant assets, implement,
verify.
