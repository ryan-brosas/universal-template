<!-- capsule-v2 -->
# DynamicToolset — factory-evaluated toolset with per-run-step lifecycle management

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter builds a toolset from a factory function that takes the run context, how does it decide when to evaluate the factory, and how does it manage the inner toolset's enter/exit lifecycle across run steps without double-exiting?

## DynamicToolset factory + lifecycle
**Path/Symbol:** `pydantic_ai/toolsets/_dynamic.py:DynamicToolset` (20-157).
**Signature:** `DynamicToolset(toolset_func, *, per_run_step=True, id=None)`; `ToolsetFunc = (ctx) -> AbstractToolset | None | Awaitable[...]`.
**Data Shape:** `_toolset` holds the currently-active inner toolset (or `None`). `per_run_step` controls factory re-evaluation cadence.

### Decisive source
```python
async def for_run(self, ctx):
    new = DynamicToolset(self.toolset_func, per_run_step=self.per_run_step, id=self._id)
    if not self.per_run_step:
        new._toolset = await new._evaluate_factory(ctx)   # only chance
    return new

async def for_run_step(self, ctx):
    if not self.per_run_step:
        return self
    new_toolset = await self._evaluate_factory(ctx)
    if new_toolset is self._toolset:
        return self
    old_toolset = self._toolset
    self._toolset = None          # detach BEFORE exiting, so __aexit__ can't double-exit
    if old_toolset is not None:
        await old_toolset.__aexit__(None, None, None)
    await self._enter_inner_toolset(new_toolset)
    return self

async def _enter_inner_toolset(self, toolset):
    self._toolset = None          # only register after successful __aenter__
    if toolset is None:
        return
    await toolset.__aenter__()
    self._toolset = toolset
```

**Flow:** `for_run` creates a fresh copy; with `per_run_step=False` it evaluates the factory now (the only chance); with `per_run_step=True` it defers to `for_run_step`. `for_run_step` re-evaluates the factory each step; if the new toolset is the same instance it returns `self` unchanged; otherwise it detaches the old toolset (sets `_toolset=None` FIRST so a failing exit can't double-exit), exits the old, then enters the new via `_enter_inner_toolset` (which only registers the inner after a successful `__aenter__`). `__aexit__` exits the active inner and clears it in a `finally`.
**Invariant:** The detach-before-exit and register-after-enter ordering guarantees `__aexit__` is never called on a toolset that was never entered (or already exited). `per_run_step=False` evaluates exactly once per run; `True` re-evaluates each step. `__eq__` compares factory identity + flags (used for dedup).
**Probe:** `tests/test_toolsets.py:test_dynamic_toolset` (1378), `test_dynamic_toolset_enter_failure_does_not_exit_unentered_toolset` (1450), `test_dynamic_toolset_aenter_failure_does_not_exit_unentered_toolset` (1513), `test_dynamic_toolset_old_aexit_failure_does_not_store_new_toolset` (1550) — the lifecycle-ordering invariants are directly pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "DynamicToolset for_run_step _enter_inner_toolset", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the factory-evaluation cadence (per_run vs per_run_step) and the detach-before-exit / register-after-enter lifecycle ordering; adapt the `id` requirement for durable-execution hosts; omit nothing — the double-exit guard is the portable invariant. Coverage clean.
