<!-- capsule-v2 -->
# Guard middleware family (mode / permission / safety / budget / retry)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/{mode,permission,tool_safety,coding_sandbox_safety,e2b_sandbox_guard,budget_guard,retry}.py` (all read whole).

## Path/Symbol
- `enforce_mode(mode)` (mode.py :19) + `_ALWAYS_ALLOWED_IN_PLAN_MODE = {"clarify","task_complete","list_toolsets","fetch_tools"}` (:9) + `_risk_from_tags` (:12)
- `require_permission(allowlist, denylist)` (permission.py :8) — allowlist XOR denylist, name-based
- `enforce_tool_safety()` (tool_safety.py :40) — shell/SQL regex denylists (`rm -rf /`, fork bomb, `mkfs.`, `dd of=/dev/sd*`, `drop database`) keyed on tool NAME sets {run_shell, execute_code} / {db_query}
- `coding_sandbox_safety(max_code_size=50_000, blocked_patterns=None, allow_url_packages=False)` (:48) — code denylist incl. `shutil.rmtree("/")`, `/dev/tcp/`, `nc -e`, `stratum+tcp://`; package-spec check rejects `git+`/`file:`/`://`
- `e2b_sandbox_guard(max_timeout=120.0, max_cumulative_s=None)` (:30) — closure `cumulative["total"]` accumulates REQUESTED timeouts
- `require_budget(budget_manager)` (budget_guard.py :10) — BudgetExceeded → ctx.deny
- `retry_model_call(config)` (retry.py :35) — Wrapper on PRE_MODEL_CALL; retries only `TransportError` with `.retryable` and status in `config.retryable_status_codes` (None status = trust transport's flag)

## Decisive source
```python
# mode.py: the prompt section only TELLS the model it's in plan mode;
# THIS middleware is the actual boundary — mode never bypasses hooks.
risk = _risk_from_tags(ctx.tags)
if risk != RiskLevel.LOW:
    ctx.deny(f"...plan mode is read-only...")
```
```python
# retry.py — why a Wrapper, not a Pipeline:
# a retry policy needs to call "the rest of the chain" an arbitrary number
# of times, which a Pipeline's single-pass next() can't express.
```

## Invariant
Five INDEPENDENT layers that must not be conflated: permission = name lists; mode = risk-tag policy (harness/meta tools exempt); tool_safety/coding_sandbox_safety = literal-text defense-in-depth that fires regardless of risk class or approval setting ("a HIGH-risk tool set to AUTO_APPROVE should still refuse rm -rf /"); e2b guard = billing ceiling (requested-not-actual seconds, coarse by design); budget = manager state; retry = re-invocable chain (Wrapper). Confinement/setrlimit stay the REAL boundary — these are cheap early nets.

## Probe
`tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py`: `test_permission_hook_with_allowlist` (:243), `test_retry_hook` (:248), `test_tool_safety_hook` (:253), `test_e2b_backend_registers_factory_and_auto_guard_hook` (:198), `test_local_backend_registers_coding_tools_and_auto_safety_hook` (:185). Regex-ladder behavior itself has no dedicated unit tests — coverage caveat recorded.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["enforce_mode","enforce_tool_safety","retry_model_call"]'`

## Verdict
ADAPT as one family capsule: porters must keep the layers separate and reproduce which event each rides (PRE_TOOL_USE vs Wrapper(PRE_MODEL_CALL)).
