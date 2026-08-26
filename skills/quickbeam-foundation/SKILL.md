---
name: quickbeam-foundation
description: "Use when porting embedded JS execution sandboxes on the BEAM (QuickJS/duktape-style engines in Elixir/Erlang), GenServer↔NIF async ref protocols, runtime/context pools with reset-on-checkin, bytecode verify-pin-evaluate pipelines with hard resource limits, optional JIT tiers over untrusted input (single-flight compile caches, validated deopt, stack dataflow verification), or TS bundler resolution ladders."
---
# QuickBEAM: JavaScript-runtime-on-the-BEAM foundations

## Use this for
Use when porting embedded JS execution sandboxes (QuickJS/duktape-style engines hosted in a VM or server), runtime-per-request vs context-per-connection pooling, GenServer↔NIF async ref protocols, BEAM-side Web API backends (fetch/URL/storage/broadcast), bytecode verify-pin-evaluate pipelines with hard resource limits, or TS bundler resolution ladders. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/runtime-genserver-ref-pending.md` — GenServer eval/call seam: NIF refs, pending transforms, :infinity timeouts.
- `references/script-load-handshake.md` — start_link blocks on a ref-tagged script_loaded message; 30 s cap.
- `references/handler-dispatch-task-salvage.md` — beam_call dispatch ladder: missing → reject; plain fn → Task; {:with_caller, f}.
- `references/server-macro-shared-clauses.md` — `use QuickBEAM.Server` injects handle_call clauses + nif_* dispatch hooks.
- `references/pool-reset-reinit-checkin.md` — NimblePool worker whose reset failure removes it from the pool.
- `references/context-pool-single-thread-multicontext.md` — one JSRuntime thread hosting many contexts, round-robin placement.
- `references/drain-callback-promise-pump.md` — re-entrant pool drain callback that pumps resolve/reject mid-await.
- `references/timer-min-dequeue-deadline.md` — min-timer bounded blocking dequeue + shared interrupt deadline.
- `references/context-lifecycle-rd-map.md` — rd_map registration ordering and rollback on create failure.
- `references/context-bytecode-cache.md` — persistent_term MD5-keyed bytecode cache for builtin polyfills.
- `references/context-worker-bootstrap.md` — Worker emulation as an apis:false child Context + onmessage setter trap.
- `references/vm-isolation-spawn-opt.md` — per-eval worker process: max_heap_size kill + timeout kill + DOWN mapping.
- `references/vm-event-loop-drive.md` — owner-local event loop: jobs → host replies → promise_deadlock.
- `references/vm-pin-store-lease.md` — idempotent pin-by-identity in fixed slots; checkout/verify_identity/checkin lease.
- `references/fetch-httpc-sync-invert.md` — sync:false httpc inverted into a synchronous fetch with ETS cancel registry.
- `references/url-component-contract.md` — WHATWG-shaped components from :uri_string; default-port elision.
- `references/web-api-beam-backends.md` — localStorage→public ETS; BroadcastChannel→:pg scopes; SSE via stream:self.
- `references/bundler-collect-rewrite.md` — DFS import collection, specifier rewrite, process-dict tracking, throw-based abort.
- `references/js-error-dialect.md` — VM reason tuples → {name,message} → JSError struct with synthesized stack.
- `references/beam-api-boundary-funcs.md` — UUIDv7 atomics, PBKDF2 envelope, XML→map, atom-registration hazards.
- `references/compiler-tier-action-algebra.md` — bounded BEAM JIT tier: 4-action contract, capped decision memo, step-fuel credit.
- `references/compiler-deopt-validated-boundary.md` — validate-at-construction before-instruction deopt records the interpreter can trust.
- `references/compiler-contract-slot-pool-keys.md` — deterministic SHA-256 artifact keys over a fixed 32-slot atom pool.
- `references/compiler-pool-single-flight-lease.md` — keyed single-flight compiles under max_heap+timeout, LRU lease slots, quarantine, drain.
- `references/pure-profile-bounded-plan.md` — candidacy prefilter + triple-bounded lowering plans; generated code delegates, never inlines.
- `references/bytecode-envelope-checksum-varint.md` — verify-first QuickJS checksum envelope + varint readers + pre-parse resource caps.
- `references/stack-verifier-dataflow.md` — worklist (depth, catch) join verifier whose levels are reused by the compiler tier.
- `references/code-emitter-form-envelope.md` — five-gate forms envelope (count/bytes/whitelist/placeholder/export) into warning-free `:compile.forms`.
- `references/code-import-closed-allowlist.md` — beam_lib imports chunk checked against a closed MFA MapSet after emit AND before load.
- `references/code-artifact-digest-revalidation.md` — sha256 stamp-at-construction revalidated immediately before `:code.load_binary` (TOCTOU gate).
- `references/code-lifecycle-soft-purge-slots.md` — soft-purge-only retirement → slot quarantine; install only into empty slots; no in-place swap, no kill.
- `references/runtime-block-charge-exact-deopt.md` — owner→memory→all-or-nothing step charging; deopt before partial blocks; 256-op cap re-checked at runtime.
- `references/runtime-scalar-state-roundtrip.md` — guard-pinned compact {frame,pc,args,locals,stack} tuples rebuilt into canonical frames at every tier exit.

## Capsule map
- **Runtime spine** — `runtime-genserver-ref-pending`, `script-load-handshake`, `handler-dispatch-task-salvage`, `server-macro-shared-clauses`: the GenServer/NIF protocol every JS call rides on.
- **Pool planes** — `pool-reset-reinit-checkin`, `context-pool-single-thread-multicontext`, `drain-callback-promise-pump`, `timer-min-dequeue-deadline`: heavyweight resettable runtimes vs lightweight multi-context threads, plus the concurrency tricks that make the latter correct.
- **Context lifecycle** — `context-lifecycle-rd-map`, `context-bytecode-cache`, `context-worker-bootstrap`: creation/teardown, cheap polyfill installs, Web-Worker emulation over child contexts.
- **Isolated VM subsystem** — `vm-isolation-spawn-opt`, `vm-event-loop-drive`, `vm-pin-store-lease`: pure-Elixir bytecode interpreter with spawn_opt containment, a no-polling event loop, and a bounded pin store.
- **Web API plane** — `fetch-httpc-sync-invert`, `url-component-contract`, `web-api-beam-backends`, `bundler-collect-rewrite`: browser-flavored APIs implemented as BEAM handler functions.
- **Error & boundary** — `js-error-dialect`, `beam-api-boundary-funcs`: exception translation and the misc BEAM function surface exposed to JS.
- **Compiled-execution tier** — `bytecode-envelope-checksum-varint`, `stack-verifier-dataflow`, `pure-profile-bounded-plan`, `compiler-contract-slot-pool-keys`, `compiler-pool-single-flight-lease`, `compiler-tier-action-algebra`, `compiler-deopt-validated-boundary`: the verify-first bytecode envelope, stack dataflow proof, bounded lowering to generated Elixir modules, atom-safe identity keys, single-flight leased module pool, and the validated deopt handoff back to the interpreter.
- **Generated-code install & ABI plane** — `code-emitter-form-envelope`, `code-import-closed-allowlist`, `code-artifact-digest-revalidation`, `code-lifecycle-soft-purge-slots`, `runtime-block-charge-exact-deopt`, `runtime-scalar-state-roundtrip`: bounded forms→binary emission, closed import allowlist, digest TOCTOU gate, soft-purge slot lifecycle, exact block charging, and the scalar compact-state round-trip across the versioned runtime ABI.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
QuickBEAM (MIT), `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory project `quickbeam` (canonical re-index 2026-08-25, FULL, ready: 21,571 nodes / 103,395 edges, head_sha == base_sha == pin; the prior `ext-quickbeam` project name is retired — revalidate against `quickbeam`). Passes 1–N before 2026-08-25 produced the original 20 capsules without a work record; pass 1 recorded in inspo/quickbeam-work/ added the Compiled-execution tier group (+7 capsule-v2); pass 2 (same pin) added the Generated-code install & ABI plane group (+6 capsule-v2: code-emitter-form-envelope, code-import-closed-allowlist, code-artifact-digest-revalidation, code-lifecycle-soft-purge-slots, runtime-block-charge-exact-deopt, runtime-scalar-state-roundtrip). Parse-partial ×342 are vendored C under priv/c_src (lexbor/quickjs/wamr) plus examples/ssr/priv/js/app.jsx and test/support/test_addon.c — none cited; not_indexed = .git + priv/vendor dirs, bun.lock, one fuzz .bin fixture.

## Full view (memory graph)
Revalidate `quickbeam` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note the vendored-C parse_partial mass inflates node counts; first-party seams live under lib/quickbeam/** and priv/ts/**. BM25 search_graph works well for Elixir/Zig symbols; doc-page style queries need file-stem search_code fallbacks only outside lib/.

## Boundaries
Adopt pure contracts: the ref-tagged pending map, reset-on-checkin pool semantics, single-thread-multi-context scheduling, drain-callback pumping, spawn_opt evaluation containment, bytecode verify/pin/lease pipeline, URL component shaping, error dialect translation. Adapt host-specific integrations: QuickJS/Zig NIF internals, lexbor DOM, OXC toolchain calls, OTP :httpc/:pg/:ets primitives to your host equivalents. Omit product behavior: priv/ts web-API JavaScript surface details, examples/, bench/, fuzz/, npm packaging, mix tasks.
