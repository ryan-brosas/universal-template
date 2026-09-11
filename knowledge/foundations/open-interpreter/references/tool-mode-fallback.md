<!-- capsule-v2 -->
# tool-mode-fallback — when do direct tools get replaced by exec, and what happens when the host is missing?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How does a harness switch between normal tool-calling and code mode without bricking turns?

## effective_tool_mode degradation ladder
**Path/Symbol:** `codex-rs/core/src/tools/mod.rs` : `effective_tool_mode` (:84-94); `core/src/tools/code_mode/mod.rs` : `take_unavailable_warning` (:101-115), lazy session init (:209-231).
**Data Shape:** ToolMode::Direct | CodeMode | CodeModeOnly; availability captured at construction from provider (executable-exists probe).

### Decisive source
```rust
if !turn_context.code_mode_available
    && requested_tool_mode == ToolMode::CodeMode
    && !turn_context.config.code_mode.disable_in_process_fallback
{
    ToolMode::Direct          // graceful degrade, once-per-process warning
} // CodeModeOnly never degrades: "Code mode will fail closed"
```

**Flow:** warning is emitted ONCE (`unavailable_warning_emitted.swap(true)`) with the remedy text (`features.code_mode_host` + install hint); behavior differs by mode — Direct falls back, CodeModeOnly fails closed. Session creation is lazy (`OnceCell::get_or_try_init`) and re-checks `shutting_down` on BOTH sides of the await; an unused service never spawns a host.
**Invariant:** Availability is sampled at startup but session creation can still fail later — every path re-validates against shutdown state to avoid initializing during drain. `interrupt_active_cells` terminates only cells with dispatch gates (the broker's active set) and tolerates individual failures with warnings.
**Probe:** thread_manager_tests.rs + config_tests.rs at pin exercise mode selection; mod.rs shutdown test pins the Err-path join.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "effective_tool_mode take_unavailable_warning disable_in_process_fallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt three-mode selection with one-shot degraded-mode warning and fail-closed-only-mode semantics. Adapt config keys. Omit product copy.
