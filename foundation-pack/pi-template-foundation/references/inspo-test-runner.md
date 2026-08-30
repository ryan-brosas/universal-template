<!-- capsule-v2 -->
# Inspiration-repo smoke runner — how do you prove third-party inspiration suites pass before building foundations on them?

**Source:** pi-template MIT `foundations-sync@37e9bc1736b7`; Codebase Memory `pi-template`. **Question:** What install-and-run ladder gives honest PASS/FAIL/NO-TESTS verdicts across heterogeneous Python repos with one command?

## uv venv + extras fallback ladder + pytest exit-code triage
**Path/Symbol:** `scripts/run-inspo-tests.py:test_python_repo` (lines 29–57); env knobs `INSPO_DIR` (default `/mnt/hdd/utopia/inspo`), `UV_BIN`.
**Signature:** `test_python_repo(name: str) -> None` mutating global `RESULTS[name] = (status, tail)`; statuses PASS / FAIL / ERROR / NO TESTS.
**Data Shape:** per-target venv at `<repo>/.venv`; captured combined output tails (200–2000 chars) as evidence.

### Decisive source
```python
rc, out = run([UV, "pip", "install", "--python", f"{venv}/bin/python", "-e", ".[test]"], path, timeout=600)
if rc != 0:
    rc, out = run([UV, "pip", "install", "--python", f"{venv}/bin/python", "-e", ".[dev]"], path, timeout=600)
if rc != 0:
    rc, out = run([UV, "pip", "install", "--python", f"{venv}/bin/python", "-e", "."], path, timeout=600)
...
rc, out = run([py, "-m", "pytest", "-q", "--ignore=tests/embeddings", "--ignore=tests/llms"], path)
if rc == 0:
    RESULTS[name] = ("PASS", out[-200:])
elif rc == 5:  # no tests collected
    RESULTS[name] = ("NO TESTS", out[-200:])
else:
    RESULTS[name] = ("FAIL", out[-300:])
```

**Flow:** `uv venv .venv` (120s) → editable-install LADDER `-e .[test]` → `-e .[dev]` → `-e .` (first success wins) → force-install `pytest pytest-asyncio` into the venv (repos with nonstandard extras still get a runner) → `pytest -q` with import-heavy optional dirs ignored → triage by exit code: 0 PASS, 5 NO TESTS (pytest's "no tests collected" — a distinct, expected outcome for fixture-only repos), anything else FAIL; install/venv failures are ERROR, not FAIL. Process exit 0 iff EVERY target PASSed; empty target list exits 0 with empty summary.
`--all` mode auto-discovers targets = inspo dirs having (`pyproject.toml` OR `requirements.txt`) AND (`tests/` OR `test/`).
**Invariant:** "no tests" must be distinguishable from failure — a smoke harness that conflates them either lies about coverage or blocks fixture-only repos.

**Probe:** `python3 scripts/run-inspo-tests.py` (no args) executed live at the pin → empty SUMMARY, exit 0 (observed 2026-08-25). Targeted use: `python3 scripts/run-inspo-tests.py <repo>`. This is the upstream of every mining lane's "runner available" claim.

## Get live surrounding code
**Retrieve:** (executed at the pin)
```ts
await mcp.codebase_memory.search_graph({ project: "pi-template", query: "inspo test runner uv venv pytest no tests collected", limit: 5 });
// -> pi-template.scripts.run-inspo-tests.test_python_repo Function scripts/run-inspo-tests.py 29-57
```

## Verdict
Adopt the extras ladder order and the rc==5 NO-TESTS triage verbatim. Adapt the ignore list (`tests/embeddings`, `tests/llms` = optional cloud-dependent imports) to each target's known-heavy dirs; keep timeouts per stage (120s venv / 600s installs / default run). Omit the hardcoded INSPO_DIR default — parameterize it.
