<!-- capsule-v2 -->
# Sandbox PRE_TOOL_USE guard pair — which checks run before a sandbox is provisioned, and why are they not the security boundary?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What cheap deterministic gates belong in front of `run_code`/`install_packages` without duplicating kernel-level enforcement?

## coding_sandbox_safety denylist + e2b-only billing guard, both auto-added
**Path/Symbol:** `backend/python/app/agent_loop_lib/hooks/middleware/builtin/coding_sandbox_safety.py:coding_sandbox_safety` (L29–91); twin `builtin/e2b_sandbox_guard.py:e2b_sandbox_guard` (L30–60); auto-add ladders `control_plane/control_plane.py:676–699`.
**Signature:** `coding_sandbox_safety(max_code_size=50_000, blocked_patterns=None, allow_url_packages=False)`; `e2b_sandbox_guard(max_timeout=120.0, max_cumulative_s=None)` — both async `(ctx: ToolCallContext, next_fn)` factories registered under `"/toolsets/coding_sandbox/**"`.
**Data Shape:** Reads `ctx.tool_input["code"]` (str) and `["packages"]` (list[str]) / `["timeout"]` (number); denies via `ctx.deny(reason)`; cumulative budget kept in a closure dict — one ControlPlane instance = one budget lifetime.

### Decisive source
```python
# Module docstring is the contract — a porter MUST keep this framing:
"""Explicitly DEFENSE-IN-DEPTH: kernel confinement (sandbox/confinement.py)
plus setrlimit (sandbox/coding/executor.py) are the real security boundary
... This middleware only catches obvious accidents/abuse cheaply and early,
before a sandbox is even provisioned ... process.exit/sys.exit are
deliberately NOT blocked — harmless inside a confined subprocess."""

_DANGEROUS_CODE_PATTERNS = [ rm -rf /, shutil.rmtree("/"), fork bomb,
    /dev/tcp/, nc -e /bin/sh, stratum+tcp:// ]        # + config extra patterns

# e2b twin — requested timeout is the proxy for cost (POST has no wall clock):
if max_cumulative_s is not None and cumulative["total"] > max_cumulative_s:
    ctx.deny("E2B cumulative sandbox time budget exhausted for this session")
    return
cumulative["total"] += requested   # counts REQUESTED seconds, pre-execution

# control_plane auto-add ladder (explicit hooks entry skips the auto-add):
if cfg.coding_sandbox.enabled and "coding_sandbox_safety" not in cfg.hooks: ...
if cfg.coding_sandbox.enabled and cfg.coding_sandbox.backend == "e2b" \
   and "e2b_sandbox_guard" not in cfg.hooks: ...
```

**Flow:** PRE_TOOL_USE on the sandbox subtree → safety middleware size-caps code, regex-denies destructive/reverse-shell/fork-bomb/mining idioms and URL/VCS/`://` package specs (unless `allow_url_packages`) → e2b guard (only when backend=="e2b") caps per-call timeout and accumulates requested seconds against an optional session budget → only then does provisioning/execution begin, where confinement+rlimits+egress veto do the real enforcement.
**Invariant:** (1) These guards are EARLY+CHEAP filters layered OVER kernel confinement/setrlimit/egress — never a replacement; treating a denylist as the boundary is the porting error. (2) `process.exit`/`sys.exit` stay allowed inside a confined subprocess. (3) The billing guard is backend-scoped (`backend=="e2b"` only) so local-backend users pay zero overhead. (4) Cumulative accounting counts REQUESTED timeout, not measured duration — coarse by design. (5) Auto-add respects explicit `hooks=[...]` entries (absence check), consistent with every other safety middleware in start().
**Probe:** `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py:258–264` pins both middlewares' explicit registration through ControlPlane wiring (:189 comment documents the auto-add expectation). Pattern-level deny behavior itself has no dedicated unit test upstream — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "coding_sandbox_safety e2b_sandbox_guard ctx.deny max_timeout", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer split (static accident filter vs real confinement) + backend-scoped billing guard + absence-check auto-adds scoped to `/toolsets/coding_sandbox/**`. Adapt denylist patterns to host risk profile; keep `allow_url_packages` as the escape hatch since EnvironmentManager independently re-validates specs at install time. Omit nothing portable. Coverage caveat: deny-branch behavior untested upstream; wiring pinned.
