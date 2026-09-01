# Reference retrieval + leverage discovery fixture (minimal)

Simulates a project with existing frontend/backend reference assets.
Used by `scripts/reference-retrieval-fixture.py --selftest`.

Companion leverage assets live in `scripts/fixtures/leverage-discovery/`.

**Organic agent eval (manual/advisory):** give a normal request such as
"Add a dashboard settings page using our existing patterns." Do not mention
`reference/`, `foundation-pack/`, or skill names. Inspect transcript/tool
calls for: project source read, reference inventory, `search-leverage` (or
equivalent), selective load of relevant matches, implementation, verification.
