<!-- capsule-v2 -->
# Orchestrator JSON health plane — how does a trusted orchestrator verify "my exact named daemon is healthy" without the CLI ever spawning, repairing, or discovering a different browser?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** What contract lets an automation layer gate on daemon health with zero side effects, and how is that gate wired into both a JSON report and the exec kernel?

## Fail-closed CDP health probe + non-networked JSON doctor
**Path/Symbol:** `src/browser_harness/admin.py`: `require_existing_daemon` (:454-473), `run_doctor_json` (:1097-1123); `src/browser_harness/run.py`: CLI grammar (:314-316) and exec-kernel veto (:382-397).

**Signature:** `def require_existing_daemon(name=None) -> None` (raises `RuntimeError`); `def run_doctor_json(require_existing_daemon=False) -> int` (exit code).

**Data Shape:** probe response must be a dict containing `"result"` (a real CDP reply); JSON report keys: `schema_version` (literal 1), `healthy`, `require_existing_daemon`, `version` (`_version() or None`), `install_mode`, `chrome_running` (`None` in strict mode), `daemon: {name, alive, browser_ready}`; printed `json.dumps(report, sort_keys=True)`.

### Decisive source
```python
def require_existing_daemon(name=None):
    """Require a healthy existing daemon without spawning or reconnecting.

    Trusted orchestrators use this after they provision a scoped CDP transport.
    Failing closed prevents a later CLI call from silently discovering a
    different local Chrome when that orchestrator-owned daemon dies.
    """
    daemon_name = name or NAME
    if not daemon_alive(daemon_name):
        raise RuntimeError(f"required daemon {daemon_name!r} is not running")
    try:
        s, token = ipc.connect(daemon_name, timeout=3.0)
        try:
            resp = ipc.request(s, token, {"method": "Target.getTargets", "params": {}})
        finally:
            s.close()
    except Exception as exc:
        raise RuntimeError(f"required daemon {daemon_name!r} is unhealthy: {exc}") from exc
    if not isinstance(resp, dict) or "result" not in resp:
        raise RuntimeError(f"required daemon {daemon_name!r} failed its CDP health check")
```

**Flow:** `require_existing_daemon`: liveness gate → one-shot IPC connect (3s timeout) → real `Target.getTargets` over IPC (must go through `ipc.connect` so Windows TCP-loopback daemons pass too) → dict-with-`"result"` required; every failure raises *before* anything is spawned, repaired, or auto-discovered. `run_doctor_json(strict)`: strict mode skips `_chrome_running()` entirely (non-networked) and computes `healthy = daemon AND browser_ready`; loose mode allows `browser_ready OR (chrome AND daemon)`; exit code is `0 if healthy else 1`. Exec-kernel wiring: `BH_REQUIRE_EXISTING_DAEMON=1` replaces BOTH the opt-in cloud autospan AND `ensure_daemon()` for non-cloud-admin scripts; the `doctor` subcommand grammar admits only duplicate-free subsets of `{--json, --require-existing-daemon}` that contain `--json`, else usage+exit 2.

**Invariant:** In strict/orchestrator mode nothing may start, repair, or discover a browser: a dead scoped daemon must fail loudly rather than let a later CLI call silently attach to some other local Chrome. The JSON schema is stable (`schema_version: 1`, sorted keys) so machines can diff it. Note the deliberate asymmetry: `ensure_daemon`'s stale path probes the same way but then *repairs*, while `require_existing_daemon` never repairs.

**Probe:** `tests/unit/test_admin.py` — `test_require_existing_daemon_fails_without_spawning` (:52-56: `RuntimeError` "required daemon 'scoped' is not running" when `daemon_alive` False); `test_require_existing_daemon_probes_cdp` (:59-67: asserts `"method": "Target.getTargets"` was sent and socket closed). `tests/unit/test_run.py` — `test_require_existing_daemon_never_auto_starts` (:24-34: `require_existing_daemon` called once, `ensure_daemon` NOT called); `test_cli_doctor_rejects_unknown_flags` (:261-267: usage + exit 2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "doctor json healthy strict report schema", limit: 10 });
```
Resolves `admin.run_doctor_json` :1097-1123 and the doctor family; `get_code_snippet` on `admin.require_existing_daemon` returns the exact body above (verified live this pass).

## Verdict
Adopt fail-closed health checks that distinguish "alive" from "actually serving CDP", stable-versioned JSON reports, and env kill-switches that demote repair into verification; adapt error-message phrasing (they double as agent instructions) and exit-code conventions; omit Browser Use specifics. Coverage caveat: none — direct unit tests exist at this pin on both the admin and run sides; all four were executed GREEN in this lane's ambient suite run.
