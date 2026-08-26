<!-- capsule-v2 -->
# pydevd product personality flags — one debugger source, two products: where do behavior deltas live?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** How does shared pydevd source express PyCharm-specific protocol behavior without runtime detection?

## Import-time patched constants + derived flags
**Path/Symbol:** `plugins/python-ce/helpers/pydev/_pydevd_bundle/pydevd_constants.py`:116 (`IS_PYCHARM_ATTACH`), :213 (`IS_PYCHARM = True`), :221 (`GOTO_HAS_RESPONSE = IS_PYCHARM`).
**Signature:** module-level assignments evaluated once at import.
**Data Shape:** booleans; consumers derive further constants from them at import time.

### Decisive source
```python
IS_PYCHARM_ATTACH = os.getenv('PYCHARM_ATTACH') == 'True'
...
IS_PYCHARM = True          # <- hardcoded in THIS shipped copy (build-time patch)

# If True, CMD_SET_NEXT_STATEMENT and CMD_RUN_TO_LINE commands have responses indicating success or failure.
GOTO_HAS_RESPONSE = IS_PYCHARM
```
Both speedup selectors also branch on it (`if not IS_PYCHARM: log_error_once("warning: Debugger speedups ...")` else `show_tracing_warning = are_setuptools_available`).

**Flow:** upstream ships one tree → each product's build stamps the personality constant → import computes derived flags (`GOTO_HAS_RESPONSE` gates whether `CMD_SET_NEXT_STATEMENT`/`CMD_RUN_TO_LINE` send a response message) → code paths read the CONSTANTS, never re-detect the host. `PYCHARM_ATTACH=True` env marks remote-attach boots of the same kernel.
**Invariant:** Personality is an IMPORT-TIME fact, not a runtime probe: porting the flag means porting every constant derived from it in the same module, and any consumer added later must keep deriving (not detecting). Warning suppression rides the same flag — PyCharm defers (`show_*_warning`) instead of logging.
**Probe:** executed 2026-08-25 — `PASS IS_PYCHARM=True hardcoded :213`, `PASS GOTO_HAS_RESPONSE=IS_PYCHARM :221`, `PASS PYCHARM_ATTACH env gate :116` (line-indexed asserts from install copy).
**Coverage caveat:** module-level constant assignments are not symbol-searchable in the graph; evidence = direct read + `check_index_coverage` `no_recorded_issue` for the file (EXECUTED) — graph side corroborated by the EnvVar plane (`__env__PYDEVD_USE_CYTHON` node returned by search).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ paths: ["plugins/python-ce/helpers/pydev/_pydevd_bundle/pydevd_constants.py"] });
// -> status no_recorded_issue, freshness metadata_match — EXECUTED
```

## Verdict
Adopt build-time personality stamping with derived-constant chains for cross-product kernels. Adapt flag names/ranges. Omit the Python-version ladder scaffolding around them.