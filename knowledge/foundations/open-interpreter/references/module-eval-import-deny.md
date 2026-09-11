<!-- capsule-v2 -->
# module-eval-import-deny — how is the exec source evaluated and why do imports always fail?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How does the main module run as ESM, and what happens on `import` statements?

## evaluate_main_module + resolve_module
**Path/Symbol:** `codex-rs/code-mode-runtime/src/runtime/module_loader.rs` : `evaluate_main_module` (:11-58), `resolve_module` (:216-228), `dynamic_import_callback` (:66-105).
**Data Shape:** compiled as ESM with resource name `exec_main.mjs`; returns the top-level promise (or None for synchronous completion / clean exit exception); ALL static + dynamic imports throw `"Unsupported import in exec: {specifier}"`.

### Decisive source
```rust
fn resolve_module<'s>(scope: ..., specifier: &str) -> Option<v8::Local<'s, v8::Module>> {
    if let Some(message) = v8::String::new(scope, &format!("Unsupported import in exec: {specifier}")) {
        scope.throw_exception(message.into());
    } else {
        scope.throw_exception(v8::undefined(scope).into());
    }
    None
}
```

**Flow:** compile → instantiate (resolver always throws) → evaluate → microtask checkpoint → classify result: promise pending (async script), fulfilled (done), rejected (error text unless exit sentinel). The dynamic-import callback exists to convert lazy import attempts into REJECTED PROMISES (model-visible) rather than host crashes.
**Invariant:** Because instantiation fails on any import, a syntax-valid script referencing an unresolvable module errors at instantiate time with the thrown message — porters who "support" imports without a real module registry break the no-network/no-fs guarantee. Completion detection reads ONLY the main-module promise; side-effect-only async work (unawaited promises, timers) never extends lifetime — matching the documented contract "unawaited promises are silently discarded."
**Probe:** runtime/mod.rs tests drive this end-to-end (`while(true)` termination, paused-resume output ordering); module_loader behavior pinned via service_tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "evaluate_main_module dynamic_import_callback resolve_module", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ESM main-module evaluation with universal import rejection and promise-state-only completion. Adapt error copy. Omit rusty_v8 API shapes.
