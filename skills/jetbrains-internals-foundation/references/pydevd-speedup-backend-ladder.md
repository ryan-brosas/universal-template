<!-- capsule-v2 -->
# pydevd speedup backend ladder — how does the tracer pick cython/frame-eval/PEP-669 without ever hard-failing?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** How to ship native speedups for a tracer across interpreter versions while guaranteeing a pure-Python floor?

## Three-stage ladder: cython select → frame-eval gates → PEP 669 replacement
**Path/Symbol:** `plugins/python-ce/helpers/pydev/_pydevd_bundle/pydevd_trace_dispatch.py`:10-15,41-133; `plugins/python-ce/helpers/pydev/_pydevd_frame_eval/pydevd_frame_eval_main.py`:16-66.
**Signature:** env knobs `PYDEVD_USE_CYTHON ∈ {YES,NO,<unset>}`, `PYDEVD_USE_FRAME_EVAL ∈ {YES,NO,<unset>}`; exports `trace_dispatch(py_db, frame, event, arg)`.
**Data Shape:** prebuilt artifacts ride beside the source: 28 `pydevd_cython*`/`pydevd_frame_evaluator*` `.so/.pyd` in this install — ALL darwin/win32, ZERO linux-flavored (measured), so Linux hosts run the pure-Python floor out of the box.

### Decisive source
```python
use_cython = os.getenv('PYDEVD_USE_CYTHON', None)
if not CYTHON_SUPPORTED or dirname.endswith('.egg'):   # remote-debug egg carve-out
    use_cython = 'NO'
...
except ImportError as e:
    if hasattr(e, 'version_mismatch'):
        delete_old_compiled_extensions()
    from ...pydevd_trace_dispatch_regular import trace_dispatch, ...   # pure-Python floor

# frame-eval main:
elif IS_PY311:  # PY-51730
    pass        # disabled
elif IS_PY312_OR_GREATER:  # PEP 669 tracing should be used instead.
    pass
```

**Flow:** select `trace_dispatch` implementation: forced `YES` imports the cython wrapper; `NO` imports `pydevd_trace_dispatch_regular`; unset tries cython then falls back (stale binaries self-heal via `delete_old_compiled_extensions` on `version_mismatch`). Frame-eval activates only above the cython layer and hard-disables for <3.6, ==3.6.1 (PY-37312), 3.11 (PY-51730); ≥3.12 replaces the whole mechanism with PEP 669 monitoring (`pydevd_pep_669_tracing*` modules sit in the bundle). Every degraded path logs-or-defers; execution never aborts.
**Invariant:** The ladder always terminates in a WORKING tracer: native layers are accelerators, never requirements. Version-gate exclusions cite their bug tickets in comments — treat those tickets as part of the contract.
**Probe:** executed 2026-08-25 — `PASS cython YES/NO/None ladder / egg remote carve-out / version_mismatch cleanup hook / frame-eval PY-37312 3.6.1 exclusion / PY-51730 3.11 exclusion / PEP669 replaces >=3.12` + `INFO cython artifacts: 28 | linux-flavored: 0`.

## Get live surrounding code
`Retrieve:`
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "use_cython PYDEVD_USE_CYTHON delete_old_compiled_extensions", limit: 5 });
// -> delete_old_compiled_extensions @ .../pydev/_pydevd_bundle/pydevd_trace_dispatch.py:18-37 + EnvVar node __env__PYDEVD_USE_CYTHON — EXECUTED
```

## Verdict
Adopt the degrade-to-pure-Python ladder, ticket-cited version exclusions, and the egg-dir carve-out for packaged deployments. Adapt artifact layout to your build. Omit the cython .pyx internals themselves (implementation, not contract).
