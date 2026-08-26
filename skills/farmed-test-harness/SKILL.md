---
name: farmed-test-harness
description: "Use when writing tests for code that talks to HTTP/LLM/external services — reuse the farmed test harness (cassette recording/replay, client error handling, pytest fixtures) instead of writing tests from scratch."
disable-model-invocation: true
---

# Farmed Test Harness

Reusable test patterns farmed from the inspo repos (pydantic-ai, graphrag, mem0)
so we don't reinvent them. This is "stack your leverage" applied to tests: the
good test code is already written — reuse it.

## When to Use

When writing tests for code that:
- Makes HTTP calls (→ use cassette recording/replay)
- Talks to LLM/external services (→ use cassette + client error handling)
- Needs pytest fixtures / slow-test gating (→ use the conftest patterns)

## The Farmed Assets (in `tests/harness/`)

- `cassette_utils.py` — (from pydantic-ai, 542 lines) unified verification for
  VCR HTTP cassettes and XAI protobuf cassettes. Record real responses, replay
  them in tests, verify cassette contents. Use for any HTTP/LLM integration test.
  Adapted to be standalone (no pydantic-ai imports).
- `harness_utils.py` — (from pydantic-ai + openai-agents-python) portable
  utilities: `try_import` (graceful optional-import handling), session-scoped
  `event_loop` fixture, `raise_if_exception`, and `remove_ambient_proxy_environment`
  (hermetic HTTP tests independent of host proxy config).
- `mock_async_stream.py` — (from pydantic-ai) wraps a sync iterator as an async
  stream for testing async/await code. Adapted to be standalone.
- `conftest.py` — pytest options + fixtures: `--run_slow` gating, `fake_png`
  fixture for image/screenshot tests, project-root `sys.path` setup,
  `collect_ignore_glob` to exclude subdirectories, a custom
  `pytest_terminal_summary` (failing tests first, then counts, then verdict),
  and a `--stability-threshold` option that gates flaky/load tests on a minimum
  pass rate while keeping non-stability failures hard.
- `inline_snapshot.py` — lightweight inline-snapshot wrapper (cheap stubs by
  default, real library only with `--inline-snapshot`/`--snap`).
- `fake_database.py` — in-memory fake database for hermetic, deterministic
  database-dependent tests.
- `retry_utils.py` — parse `Retry-After` headers (seconds or HTTP-date) and
  extract status codes from exception cause chains.
- `broad_assertions.py` — broad assertion helpers that target the TYPE of bug
  (all-satisfy, no-duplicates, near-duplicate detection, no-unused). A test is
  only good if it catches; make tests broad, not narrow.

## Make tests BROAD (the methodology)

- Target the TYPE of bug, not one instance. `assert_all_satisfy` catches any
  item violating an invariant; `assert_no_duplicates` / `assert_all_distinct_enough`
  catch any (near-)duplicate; `assert_no_unused` catches any dead code.
- Expand existing tests, don't create new near-identical ones.
- Test the un-fixed AND fixed versions (pre-fix fails, post-fix passes).

## How to Use

1. **HTTP/LLM tests** — use `cassette_utils.py` to record a real response once,
   then replay it in tests (fast, deterministic, no network). Verify the cassette
   caught what you expect.
2. **Slow tests** — use the `--run_slow` option from `conftest.py` to gate slow
   tests behind a flag, so the fast suite runs in CI.
3. **Client error handling** — use `client_utils.py` patterns to test API error
   paths (auth, network, rate-limit) without hitting real services.

## The Methodology (from Pillar 4)

- A test is only good if it CATCHS — test the un-fixed and fixed versions.
- Farmed tests are BROAD: the cassette pattern catches any HTTP regression, not
  one case.
- Expand the farmed harness, don't duplicate it. When a new HTTP case slips past,
  expand `cassette_utils.py` rather than writing a new one.

## Verification

- A test that records a cassette fails against the un-fixed code and passes
  against the fixed code.
- Slow tests are gated behind `--run_slow` and don't block CI.
- The farmed harness is reused, not duplicated.
