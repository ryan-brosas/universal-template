<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# open-interpreter: Code-Mode Foundation

## Use this for
Use when building or porting a JavaScript code-action loop: an `exec` freeform tool evaluated in a fresh V8 isolate with nested tools on a `tools` global, a `wait` polling twin for long-running cells, the five-phase cell state machine behind yields/termination, session store/load semantics across cells, a capability-negotiated sandbox host process with admission limits, JSON-schema→TypeScript declaration rendering under DoS budgets, and the three-mode direct/code-mode/code-mode-only fallback ladder. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./exec-tool-description-assembly.md` — which prompt sections are static vs derived, and when each appends.
- `./exec-pragma-parse.md` — first-line `// @exec:` knob parsing; what fails vs passes.
- `./v8-isolate-contract.md` — exact global surface; deleted capabilities; two-part exit sentinel.
- `./runtime-command-loop.md` — dedicated-thread V8 command/event loop; completion by promise state.
- `./cell-actor-fsm.md` — Running→Terminating→Completed→Claimed→Tombstone; initial-yield race buffer.
- `./session-store-commit.md` — when store() writes become visible; cancellation-gated commit.
- `./yield-grace-and-missing-cell.md` — 1s grace ladder; missing cell as model-readable data, never error.
- `./nested-tool-dispatch-gate.md` — broker→readiness-gate→worker pipeline for JS tool calls.
- `./callback-drain-taxonomy.md` — DrainNotifications vs Cancel; panic-to-ToolError promise bridging.
- `./exec-output-status-envelope.md` — status headers, post-truncation prepend ordering, hook exemption for wait.
- `./schema-to-typescript-budgets.md` — four-budget bounded TS rendering; degrade-to-unknown everywhere.
- `./host-handshake-limits.md` — semaphore admission, seen-session-id LRU, cancellable-request classification.
- `./process-owned-host-lifecycle.md` — lazy single host, permit-coalesced reconnects, generation-tagged opens.
- `./tool-mode-fallback.md` — Direct/CodeMode/CodeModeOnly selection and fail-closed vs graceful degradation.
- `./wait-tool-loop-contract.md` — exec+wait pairing; request-carried tool snapshots with stripped schemas.
- `./session-runtime-shutdown.md` — deadlock-free drain via close-under-registry-lock.
- `./host-peer-bulk-lane.md` — permit-ledger delegate backpressure; control-vs-bulk lane discipline.
- `./store-load-helper-contract.md` — in-cell helper validation matrix; event-immediate output emission.
- `./session-limits-capability.md` — default-degrade limits negotiation; honest non-enforcement of heap caps.
- `./grpc-session-provider.md` — second transport converging on one host handler.
- `./module-eval-import-deny.md` — ESM main-module evaluation with universal import rejection.
- `./code-mode-wire-messages.md` — tagged camelCase strict wire schema; slash-method requests.
- `./exec-cell-observability.md` — once-only terminal close, trace/analytics symmetry, gate-set interrupts.
- `./code-mode-crate-topology.md` — protocol/runtime/host/provider/core layer split; single-source domain types.

## Capsule map
- **Model-facing surface** — `exec-tool-description-assembly`: section ladder with early return unless code_mode_only, once-emitted MCP preamble keyed on structural CallToolResult shape, shared identifier normalizer binding prompt↔runtime. `exec-pragma-parse`: first-line-only pragma with deny-unknown-fields and 2^53 clamps mirrored by the provider grammar. `schema-to-typescript-budgets`: per-path×2 / total×32 ref budgets + 16KB/64KB work-byte metering, always degrading to `unknown`.
- **V8 runtime kernel** — `v8-isolate-contract`: delete console/Atomics/SAB/WebAssembly before helpers; index-closure tool bindings; exit() = flag + sentinel exception. `runtime-command-loop`: std::mpsc commands in, tokio events out, microtask-checkpoint completion checks, thread-per-timer setTimeout. `module-eval-import-deny`: ESM eval as exec_main.mjs, imports always throw, promise-state-only lifetime. `store-load-helper-contract`: strict helper inputs; notify-empty rejection; serializable-store gate.
- **Cell lifecycle** — `cell-actor-fsm`: commit/delivery split over a five-phase CellState mutex; pending_initial_yield_items race buffer; biased cancel-first select; restore-on-dropped-receiver buffers. `callback-drain-taxonomy`: notifications drain on completion while tools cancel; panicked tools still resolve their JS promise as ToolError. `session-runtime-shutdown`: tracker.close() while holding the registry lock makes passed-the-check ⇒ registered atomic.
- **Session semantics** — `session-store-commit`: snapshot-in/delta-out; delta extends session map only at non-cancelled completion. `yield-grace-and-missing-cell`: ≥10s yields get +1s grace on both sides; MissingCell/ClosedCell become successful empty Results so the model self-corrects. `session-limits-capability`: trait default degrades only default limits; heap limit plumbed but deliberately unenforced locally.
- **Host boundary** — `host-handshake-limits`: try-acquire semaphores (256 req/128 cells) fail fast; session ids are capabilities via 4096 LRU; only Execute|Wait cancellable. `host-peer-bulk-lane`: owned-permit delegate backpressure at 1024; wrong-lane messages hard-reject; frame overflow becomes structured error. `process-owned-host-lifecycle`: process_group(0)+kill_on_drop+scrubbed env; Opening-state-aware shutdown driver. `code-mode-wire-messages`: deny_unknown_fields tagged schema validated at parse time.
- **Turn integration** — `nested-tool-dispatch-gate`: per-cell watch gates set after execute acceptance; synthetic `exec-{uuid}` call ids; function/freeform payload typing. `tool-mode-fallback`: one-shot degraded warning; CodeModeOnly never degrades. `wait-tool-loop-contract`: grammar mirrors parser; schemas stripped from cell snapshots; terminal close duplicated symmetrically across handlers. `exec-output-status-envelope`: status banner prepended AFTER truncation; wait hook-exempt. `exec-cell-observability`: exactly-once terminal lifecycle across execute+wait observers.
- **Composition** — `code-mode-crate-topology`: domain types live only in protocol; v8 feature flag contained in runtime; disabled provider = explicit fail-closed object. `grpc-session-provider`: all transports converge on one handle_request.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
open-interpreter (Apache-2.0), `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory project `ext-open-interpreter` (root `/mnt/hdd/utopia/inspo/external/open-interpreter`, FULL mode, 113,523n/742,028e, indexed 2026-08-23T09:11:09Z, generation_matches=true; repo is now a Rust Codex fork — the legacy Python interpreter tree is gone at this HEAD).

## Full view (memory graph)
Revalidate `ext-open-interpreter` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. All 18 cited paths returned no_recorded_issue + metadata_match at the pinned HEAD.

## Boundaries
Adopt the pure contracts: cell FSM phases, store-commit gating, grace ladders, budget-bounded schema rendering, import denial, missing-cell-as-data. Adapt transports (stdio/WebSocket/gRPC are interchangeable behind one trait), helper vocabularies, and numeric constants to your environment. Omit product-specific analytics facts, Kimi/Claude harness emulation surfaces, and install-context path resolution; the sandbox is deny-by-deletion plus V8's sandbox — do not present it as a security boundary equivalent to a OS-level jail.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`callback-drain-taxonomy.md`](./callback-drain-taxonomy.md)
- [`cell-actor-fsm.md`](./cell-actor-fsm.md)
- [`code-mode-crate-topology.md`](./code-mode-crate-topology.md)
- [`code-mode-wire-messages.md`](./code-mode-wire-messages.md)
- [`exec-cell-observability.md`](./exec-cell-observability.md)
- [`exec-output-status-envelope.md`](./exec-output-status-envelope.md)
- [`exec-pragma-parse.md`](./exec-pragma-parse.md)
- [`exec-tool-description-assembly.md`](./exec-tool-description-assembly.md)
- [`grpc-session-provider.md`](./grpc-session-provider.md)
- [`host-handshake-limits.md`](./host-handshake-limits.md)
- [`host-peer-bulk-lane.md`](./host-peer-bulk-lane.md)
- [`module-eval-import-deny.md`](./module-eval-import-deny.md)
- [`nested-tool-dispatch-gate.md`](./nested-tool-dispatch-gate.md)
- [`process-owned-host-lifecycle.md`](./process-owned-host-lifecycle.md)
- [`runtime-command-loop.md`](./runtime-command-loop.md)
- [`schema-to-typescript-budgets.md`](./schema-to-typescript-budgets.md)
- [`session-limits-capability.md`](./session-limits-capability.md)
- [`session-runtime-shutdown.md`](./session-runtime-shutdown.md)
- [`session-store-commit.md`](./session-store-commit.md)
- [`store-load-helper-contract.md`](./store-load-helper-contract.md)
- [`tool-mode-fallback.md`](./tool-mode-fallback.md)
- [`v8-isolate-contract.md`](./v8-isolate-contract.md)
- [`wait-tool-loop-contract.md`](./wait-tool-loop-contract.md)
- [`yield-grace-and-missing-cell.md`](./yield-grace-and-missing-cell.md)
