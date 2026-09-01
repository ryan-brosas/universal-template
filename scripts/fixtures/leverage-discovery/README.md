# Leverage discovery fixture

Minimal skills and foundations for deterministic discovery tests.
Used by `scripts/reference-retrieval-fixture.py --selftest`.

Organic agent eval prompt (manual/advisory):

    Add a dashboard settings page using our existing patterns.

Expected behavior (hidden rubric):

1. Inspect `scripts/fixtures/reference-retrieval-project/src/`
2. Notice `reference/` and `reference/web/` without being told
3. Run cheap `search-leverage "dashboard settings"` (or equivalent)
4. Load `dashboard-patterns` skill and/or `dashboard-settings-foundation` if useful
5. Skip `unrelated-noise-*` matches
6. Implement and verify against the project fixture
