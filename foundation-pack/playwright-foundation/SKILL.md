---
name: playwright-foundation
description: "Use when porting Playwright's client RPC architecture (GUID object trees, channel proxies, async emitters, Waiter/Progress cancellation, timeout ladders, typed error round-trips) or its child-process lifecycle kernel (spawn fd layout, graceful-close ladders, signal refcounting, cross-platform tree kill, length-prefixed pipe framing, launch readiness races)."
disable-model-invocation: true
---

# Playwright (microsoft/playwright): Client RPC & Cancellation Foundation

## Use this for
Porting any browser-automation or long-running-tool architecture where a thin client object graph talks to a heavyweight server process over an async message pipe: GUID-addressed remote objects created/adopted/disposed by the peer, a Proxy-based channel that validates params and reports API calls exactly once, an AsyncLocalStorage "zone" carrying call metadata across await boundaries without polluting server events, a hand-rolled EventEmitter whose handlers may be async and whose teardown can await them, a Waiter that races one desired event against crash/close/timeout failures while streaming structured wait-info to the server for trace viewing, a server-side ProgressController that turns timeouts into AbortSignals with a strict no-nested-races rule, a three-key timeout precedence ladder shared by every API method, and an error protocol that reconstructs typed errors (TimeoutError/TargetClosedError/AbortError) on the far side of the wire. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/connection-dispatch-lifecycle.md` — how does one message pipe serve both promise responses and object events?
- `references/guid-object-tree.md` — how do remote objects get created, adopted, GC-collected, and disposed?
- `references/proxy-channel-apiscope.md` — why is every channel a Proxy, and when does an API call get reported?
- `references/zones-asynclocalstorage.md` — how does call metadata cross awaits without leaking into server events?
- `references/eventemitter-async-safety.md` — what must a hand-rolled EventEmitter guarantee for async listeners?
- `references/subscription-mapping.md` — when do protocol events actually get subscribed on the wire?
- `references/waiter-failure-race.md` — how does waitForEvent lose to crash/close/timeout without leaking listeners?
- `references/progress-controller-server.md` — how does the server turn a deadline into cancellation?
- `references/timeout-settings-ladder.md` — which timeout wins between option, default, debug mode, and parent?
- `references/typed-error-roundtrip.md` — which errors survive the wire as classes, and how are stacks rebuilt?
- `references/library-stack-capture.md` — how does the client derive the apiName and user-only stack for a call?
- `references/abort-signal-plumbing.md` — how do user-supplied AbortSignals cancel an in-flight RPC?
- `references/long-standing-scope-terminate-close.md` — how does one peer-death event cancel every present AND future waiter, without sharing a broken stack?
- `references/deadline-poll-ladder.md` — how do you poll a flaky predicate until it passes, bounded by one monotonic deadline?
- `references/await-must-use-progress-rule.md` — how is "every awaited call is cancellable" enforced at CI time?
- `references/retry-nonretriable-taxonomy.md` — how does a retry loop wake instantly on page close, and which errors must never be retried?
- `references/launch-process-fd-layout.md` — how do you spawn a peer process so its whole tree is killable and it speaks on fds 3/4?
- `references/graceful-close-ladder.md` — how does shutdown degrade from polite protocol message to timeout to force-kill without zombies?
- `references/signal-handler-refcount.md` — how do N launched processes share SIGINT/SIGTERM/exit handlers and uninstall them at exactly the right moment?
- `references/kill-tree-portability.md` — how do you force-kill a child tree synchronously on Windows and POSIX?
- `references/pipe-transport-framing.md` — how do you frame a raw byte stream into length-prefixed messages without re-entrancy or post-close writes?
- `references/launch-ready-state-race.md` — how does launch fail fast when the peer dies before ready, with actionable startup logs?
- `references/browser-close-idempotence.md` — how does close() stay idempotent under concurrent callers and fan death out to every dependent?

## Capsule map
- **Message dispatch** — `connection-dispatch-lifecycle`: id-bearing messages resolve callbacks exactly-once (deleted before settle); id-less ones route by GUID; `close()` latches a TargetClosedError and rejects everything in flight.
- **Object lifecycle** — `guid-object-tree`: `__create__`/`__adopt__`/`__dispose__` maintain a dual-indexed (connection + parent) GUID tree; `'gc'` disposal marks `_wasCollected` so later calls throw instead of hang.
- **Channel surface** — `proxy-channel-apiscope`: a Proxy resolves each method through a Params validator; the first non-internal call in an apiZone reports once via instrumentation, retries go `internal`.
- **Async context** — `zones-asynclocalstorage`: immutable Zone chain over AsyncLocalStorage; outbound messages run under `emptyZone` so replies never inherit caller context; Waiters strip `apiZone` before waiting.
- **Event plumbing** — `eventemitter-async-safety`: single-listener fast path, snapshot iteration during emit, pending-promise sets keyed by event, and `removeAllListeners(...,{behavior:'wait'})` that awaits in-flight handlers.
- **Lazy subscriptions** — `subscription-mapping`: `on()` enables the mapped protocol event only on the first listener; `off()` disables it on the last removal; fire-and-forget with `.catch(() => {})`.
- **Wait orchestration** — `waiter-failure-race`: one Waiter races the target event against registered failure promises; `__waitInfo__` phases (before/log/after) stream trace data; dispose-on-settle removes every listener.
- **Server cancellation** — `progress-controller-server`: state machine before→running→finished/error; deadline timer and `abort()` both reject `_forceAbortPromise` and drive an AbortController; nested `race()` detection under env flag; cleanup helper for uncancellable ops.
- **Timeout resolution** — `timeout-settings-ladder`: explicit option → navigation-specific default → inspector-mode 0 → generic default → parent chain → 30s (launch path skips the generic default → 3min).
- **Error fidelity** — `typed-error-roundtrip`: client `parseError` rebuilds typed PlaywrightErrors by class name and attaches ErrorDetails + call log; the server twin deliberately returns plain Errors — porting either shape to the other side breaks typing.
- **Stack attribution** — `library-stack-capture`: deepest library→user transition names the API (`Page.click` → `page.click`); frames replace error stacks so users see their line, not the pipe.
- **Cancellation ingress** — `abort-signal-plumbing`: pre-aborted signals throw with `cause`; in-flight ones send an id-keyed `__abort__` wire event; the eventual rejection re-attaches the user's reason as `cause`; listeners removed exactly once.
- **Scope-wide death propagation** — `long-standing-scope-terminate-close`: reject() shares one Error (hard death); close() clones it per racer with captured stacks (graceful); late joiners resolve immediately; safeRace resolves a default instead of rejecting.
- **Deadline-bounded polling** — `deadline-poll-ladder`: raceAgainstDeadline discriminated union; [100,250,500,1000] consume-once backoff that never sleeps past the deadline; lastResult survives a timeout for error rendering.
- **Cancellability lint contract** — `await-must-use-progress-rule`: type-aware ESLint rule — awaited async calls inside Progress-typed functions must pass progress as first arg or live lexically inside progress.race().
- **Retry + error taxonomy** — `retry-nonretriable-taxonomy`: [0,...timeouts] zero first delay; backoff sleeps raced against Page.openScope + Frame._detachedScope via raceMultiple for instant wake; ordered five-clause throw-gate with abort-family checked first.
- **Spawn & fd layout** — `launch-process-fd-layout`: five-entry stdio (protocol on fd 3/4, stdin ignored), POSIX detached:true group leader for negative-pid tree kill, dual error-listener spawn-failure conversion, global gracefullyCloseSet/killSet registration until 'close'.
- **Shutdown ladder** — `graceful-close-ladder`: race(polite protocol close vs timeout) → rejection/timeout ⇒ sync group SIGKILL → every path awaits death+temp-dir cleanup; reentrant second close means force-kill; engines send Browser.close/Playwright.close/bidi session+close with the kBrowserCloseMessageId reply swallowed by the connection.
- **Signal refcount** — `signal-handler-refcount`: handlers installed once into a module set and removed only when killSet empties; two-press SIGINT (graceful→exit130, then immediate kill); exit handler must be sync; 30s do-not-hang forced exit.
- **Force-kill portability** — `kill-tree-portability`: sync killProcess (usable in process-'exit'); win32 `taskkill /T /F` vs POSIX `process.kill(-pid,'SIGKILL')`; idempotence guards on pid/killed/processClosed; sync rmSync twin for exit-time temp-dir removal.
- **Pipe framing** — `pipe-transport-framing`: incremental 4-byte length-prefix parser over concatenated buffers; messages delivered via next-task scheduler so handlers can safely send; throw-on-send-after-close; close deliberately lets the stream throw.
- **Launch readiness** — `launch-ready-state-race`: exitPromise raced against waitForReadyState so premature peer death unblocks instantly with captured RecentLogsCollector logs rewritten per engine into actionable text; catch paths funnel into closeOrKill; single retry only for the named glibc ld.so transient.
- **Close idempotence** — `browser-close-idempotence`: `_startedClosing` latch set before any await; late callers await the single Disconnected event; didClose fans out synchronously to contexts → downloads (TargetClosedError) → server stop → emit.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
playwright (microsoft/playwright), Apache-2.0, main @ `d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory project `ext-playwright` (42,995 nodes / 146,164 edges, FULL mode @ head==base==live HEAD, generation matches, zero drift; parse_partial ×28 confined to browser_patches C++/conf, css, docs — none cited). Pass 1 mined the client RPC kernel (`client/{connection,channelOwner,eventEmitter,waiter,timeoutSettings,errors,clientStackTrace}.ts`), the shared zone utility (`packages/utils/zones.ts`), and the server cancellation kernel (`server/progress.ts`) whole-file (~2,300 LOC). Pass 2 (2026-08-25) deepened the server-side cancellable-operation kernel via Codebase Memory project `playwright` (same checkout tree at `/mnt/hdd/utopia/inspo/playwright`, same HEAD d4e1023f, full mode, generation 2026-08-25T19:56:46Z, 42,995n/146,152e, coverage-checked clean on every cited file): +4 capsules (`long-standing-scope-terminate-close`, `deadline-poll-ladder`, `await-must-use-progress-rule`, `retry-nonretriable-taxonomy`) and a source-verified correction to the `progress-controller-server` decisive excerpt (`!this.metadata.pauseEndTime`). Pass 3 (2026-08-26) mined the browser-process launch/shutdown lifecycle at the same verified pin (project `playwright`, HEAD re-checked live, coverage no_recorded_issue ×10 across all cited source/test files): +7 capsule-v2 (`launch-process-fd-layout`, `graceful-close-ladder`, `signal-handler-refcount`, `kill-tree-portability`, `pipe-transport-framing`, `launch-ready-state-race`, `browser-close-idempotence`) over `packages/utils/processLauncher.ts`, `packages/utils/pipeTransport.ts`, `packages/utils/task.ts`, `server/browserType.ts`, `server/browser.ts`, and the per-engine `attemptToGracefullyCloseBrowser`/`doRewriteStartupLog` variants.

## Full view (memory graph)
Revalidate `playwright` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/playwright`, branch `main`, commit `d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`, FULL mode, 42,995n/146,152e, generation 2026-08-25T19:56:46Z (re-verified live in pass 3). Passes 1–2 originally cited sibling project `ext-playwright` (root `/mnt/hdd/utopia/inspo/external/playwright`, same checkout content at the same HEAD); that project is absent from `list_projects` since pass 2 — cite only `playwright`. Caveat: BM25 twins — client/server files share symbol names (`parseError`, `serializeError`); route queries by file-path terms ("client errors") and verify the returned span's file before citing. Bare short-name lookups can miss class methods (`.*_launchProcess.*` unqualified returns total 0) — use class-qualified qns or file-pattern sweeps. Source and direct tests decide shipped claims.

## Boundaries
Adopt the GUID object tree, exactly-once callback dispatch, zone-scoped API reporting, listener-count-gated subscriptions, failure-race waiting, deadline-to-AbortSignal conversion, and typed-error reconstruction as portable contracts. Adapt transport specifics (WebSocket vs stdio pipe), the generated validator/protocol layer, Node AsyncLocalStorage mechanics to your runtime, timeout constants, and log/message copy to your host. Omit the browser-specific server backends (chromium/firefox/webkit/bidi pages), the test-runner plane (`packages/playwright`), trace-viewer UI, registry/installer, and browser_patches — none are part of the RPC contract mined here.
