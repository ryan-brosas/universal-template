<!-- capsule-v2 -->
# v8-isolate-contract — what can the executed JS actually reach, and how is it installed?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** What is the exact global surface of an exec cell, and which capabilities are deliberately deleted?

## install_globals surface
**Path/Symbol:** `codex-rs/code-mode-runtime/src/runtime/globals.rs` : `install_globals` (:11-49).
**Data Shape:** deletes `console`, `Atomics`, `SharedArrayBuffer`, `WebAssembly`; installs `tools` (one function per enabled tool keyed by normalized name), `ALL_TOOLS` (`[{name, description}]`), and helpers `setTimeout/clearTimeout/text/image/audio/generatedImage/store/load/notify/yield_control/exit`. Each tool callback closes over its INDEX into `RuntimeState.enabled_tools` via template data.

### Decisive source
```rust
delete_global(scope, global, "console")?;
delete_global(scope, global, "Atomics")?;
delete_global(scope, global, "SharedArrayBuffer")?;
delete_global(scope, global, "WebAssembly")?;
...
let tools = build_tools_object(scope)?;      // per-tool fn bound by global_name
let all_tools = build_all_tools_value(scope)?;  // metadata incl. DEFERRED tools' discovery contract
```

**Flow:** fresh isolate per cell → capability deletions → helper installation → main-module evaluation. No Node, no fs, no network, no dynamic imports that resolve (`resolve_module` ALWAYS throws `"Unsupported import in exec: {specifier}"` — both static and dynamic import callbacks reject).
**Invariant:** The sandbox is deny-by-deletion on a fresh V8 isolate plus V8's own sandbox (asserted by test `linked_v8_has_sandbox_enabled`). Deletion happens BEFORE user code runs; a porter who installs helpers first still fine, but skipping deletion leaves SAB+Atomics = a real concurrency escape. Deferred tools are NOT bound on `tools` — only listed in `ALL_TOOLS` — so the prompt's "filter ALL_TOOLS" guidance matches runtime reality.
**Probe:** in-file tests at pin: `terminate_execution_stops_cpu_bound_module` (while(true) killed via `IsolateHandle::terminate_execution`), `runtime_thread_panic_is_forwarded_without_owner_supervision` (panic → `ThreadPanicked` event, never process crash).

## exit() is a sentinel exception, not a control-flow return
**Path/Symbol:** `code-mode-runtime/src/runtime/callbacks.rs` : `exit_callback` (:331-343) + `module_loader.rs` : `is_exit_exception`.
**Data Shape:** sets `state.exit_requested = true` then throws the string constant `EXIT_SENTINEL = "__codex_code_mode_exit__"`; completion classification converts that exact exception into success.
```rust
if let Some(state) = scope.get_slot_mut::<RuntimeState>() { state.exit_requested = true; }
if let Some(error) = v8::String::new(scope, EXIT_SENTINEL) { scope.throw_exception(error.into()); }
```
**Invariant:** BOTH the flag and the thrown value must match to classify as clean exit — a user script that throws the literal sentinel WITHOUT calling exit() is still an error (flag unset). Ported runtimes must keep the two-part check or early-return becomes model-visible failure.
**Probe:** module_loader tests + `is_exit_exception` gate on both evaluate path (:76-86) and rejected-promise path (:110-118).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "install_globals delete_global WebAssembly", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fresh-isolate-per-cell contract with explicit capability deletion, index-closure tool bindings, ALL_TOOLS metadata for deferred discovery, and the two-part exit sentinel. Adapt helper names to your product surface. Omit ICU/JIT init specifics (process-wide `initialize_v8` OnceLock; JIT mode is one-way).
