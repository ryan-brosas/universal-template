<!-- capsule-v2 -->
# ControlPlane composition root — what order must services be provisioned so hooks can reference them?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When one config provisions transports, tools, middleware, and stores into a shared runtime, which wiring steps have ordering constraints a porter will get wrong?

## Numbered start() pipeline with deferred + auto-add hook wiring
**Path/Symbol:** `backend/python/app/agent_loop_lib/control_plane/control_plane.py:ControlPlane.start` (L67–882), `stop` (L884–891).
**Signature:** `async def start(self) -> None`; all heavy imports are function-local (module import stays cheap; TYPE_CHECKING-only cycles avoided).

```python
# start() step order (comments in source):
# 1. Transport → TransportRegistry (lazy: factory only, no instantiation)
#    — every factory wrapped by traced_transport_factory(opik gate) FIRST,
#      so tracing is uniform regardless of provider.
# 2/3/3b. memory / knowledge / workspace backends (strict allowlist + raise
#    ValueError listing supported values on unknown names).
# 4. BudgetTracker (only if cfg.budget configured).
# 5. BUILTIN_TOOLS name→factory map; "all" sentinel registers every builtin;
#    unknown names in cfg.tools are silently ignored.
# 5b. lazy toolsets (meta-tools + grouping of REGISTERED tools only:
#    `present = [m for m in members if tool_registry.has(m)]`).
# 5d. sandbox taxonomy: os/db/browser direct; coding via SandboxManager with
#    per-backend closures (fresh uuid working dir per sandbox instance).
# 6. HookRegistry kernel — cfg.hooks loop + AUTO-ADD block below.
# 7. RoleRegistry. 8. stores (HIL/approval/checkpoint ALWAYS created;
#    state/timeline/session opt-in). 8b. SkillManager AFTER stores.
# 9. approval middleware post-wire (needs approval+hil stores ready).
# 10. AgentRuntime + AgentFactory; runtime.spec_factory = factory.from_role.

# The auto-add block (L661-698) — config convenience, defense-in-depth:
if self._budget_manager is not None and "budget_guard" not in cfg.hooks:
    kernel.on(HookEvent.PRE_TOOL_USE).use(require_budget(self._budget_manager))
if (cfg.allowlist is not None or cfg.denylist) and "permission" not in cfg.hooks:
    kernel.on(HookEvent.PRE_TOOL_USE).use(require_permission(...))
if cfg.mode != "act":
    kernel.on(HookEvent.PRE_TOOL_USE).use(enforce_mode(cfg.mode))
if cfg.coding_sandbox.enabled and "coding_sandbox_safety" not in cfg.hooks:
    kernel.on(HookEvent.PRE_TOOL_USE).use("/toolsets/coding_sandbox/**",
        coding_sandbox_safety(...))   # scoped to its own subtree only
```

**Data Shape:** `ControlPlaneConfig` drives ~20 subsystem choices; unknown backend strings raise immediately with the supported list. Stores split: HIL/approval/checkpoint are unconditional (resume + approval hook depend on them), observability stores are flags. `skill_learning` hook is a deliberate `pass` inside the cfg.hooks loop (L649–655) because it needs SkillManager + timeline store — wired onto the SAME kernel after step 8b.

### Decisive source
```python
# L650-655: "# Deferred: needs the SkillManager + timeline store, both
#  built below at step 8b/8 — wired onto this same `kernel` instance right
#  after those exist, same pattern the 'approval' hook (step 9) already
#  uses for a post-stores dependency."
#
# make_spec mode precedence (L945-949): "The global ControlPlaneConfig.mode
#  is only a fallback default — an explicit per-call override or the role's
#  own `mode` both win."   if role.mode is None and "mode" not in overrides:
#      overrides.setdefault("mode", self._config.mode)
```

**Flow:** `await cp.start()` provisions everything once → `make_spec(role)` resolves role NAME→AgentSpec (raises unless started; unknown role ⇒ ValueError with available names) → `create_agent` = `Agent(make_spec(), runtime)` cheap constructor → `__aexit__`/`stop()` closes memory provider, browser sandbox, then `sandbox_manager.destroy_all()`; idempotent (safe to call twice).

**Invariant:** three ordering rules break silently if violated: (1) middleware that captures a store (approval, skill_learning) must register AFTER those stores exist — that's why they're post-wired instead of in the main loop; (2) auto-add safety middleware fires ONLY when the feature is enabled AND not already explicitly listed — double registration would duplicate decisions/messages; (3) transport tracing wraps the FACTORY at registration, before any instantiation, so no call escapes tracing even for lazily-created transports.
**Probe:** `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py:316-329` (`TestHookAutoAdd`: mode≠act wires enforce_mode; budget+allowlist auto-add when absent from hooks), `:478-506` (`TestMakeSpec`: not-started raises, unknown role raises, config-mode fallback, explicit override wins, pinned_toolsets default from config), `:391-420` (`TestStop`: idempotent, closes memory/browser/sandboxes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ControlPlane start make_spec runtime factory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the numbered provisioning order, the always-vs-opt-in store split, and the auto-add-with-absence-check pattern. Adapt the concrete backend allowlists and config surface to host. Omit PipesHub's opik tracing gate and skill-library stack specifics if your host has other observability/learning systems. Direct tests read at HEAD (test_control_plane_coverage.py — full wiring matrix incl. adversarial stop-twice and pre-start paths).
