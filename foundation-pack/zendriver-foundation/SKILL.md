---
name: zendriver-foundation
description: "Use when porting Python CDP (Chrome DevTools Protocol) automation code — websocket command correlation, stealth browser launching, element finding across shadow roots, React-safe input injection, network interception, or Cloudflare-challenge handling — without selenium or a code-generated client."
disable-model-invocation: true
---
# zendriver: zero-dependency undetected Chrome automation foundation

## Use this for
Use when porting Python CDP (Chrome DevTools Protocol) automation code — websocket command correlation, stealth browser launching, element finding across shadow roots, React-safe input injection, network interception, or Cloudflare-challenge handling — without selenium or a code-generated client. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/transaction-generator-protocol.md` — how a cdp generator call becomes an awaited, typed result via id-correlated futures.
- `references/listener-idle-event-loop.md` — single recv task dispatching responses/events and reporting idle for `wait()`.
- `references/domain-enable-reconciliation.md` — auto-enabling handler domains before commands without fighting manual enable/disable.
- `references/oneshot-and-classfreeze.md` — the id `-2` setup side-channel and the frozen-classstate metaclass.
- `references/config-args-pipeline.md` — argv composition, managed-flag deny-guard, and kwargs-as-attributes.
- `references/executable-discovery-shortest-wins.md` — browser binary search with the shortest-path tie-break trap.
- `references/lazy-profile-and-root-sandbox.md` — deferred temp profiles per instance copy and root→no-sandbox auto-correct.
- `references/browser-start-connect-loop.md` — launch → HTTP poll → WS connection → target autodiscovery, with atexit safety.
- `references/target-inventory-events.md` — event+poll reconciliation of `browser.targets` (and the TargetCrashed no-op).
- `references/cookie-jar-storage-plane.md` — profile-wide cookies via `storage`, regex-subset pickle save/load.
- `references/find-wait-retry-ladder.md` — find/select/xpath retry cadence and their raise-vs-return contracts.
- `references/stale-node-retry-once.md` — "could not find node" recovery bounded by the `__last` sentinel.
- `references/evaluate-js-dumps.md` — value vs deep serialization plus the two-variant JS object dumper.
- `references/event-close-get-futures.md` — one-shot event futures for get/close and the expectation classes' hygiene.
- `references/element-attr-dual-plane.md` — underscore rule separating python state from HTML attributes (ContraDict).
- `references/react-native-setter-inputs.md` — native prototype setter + explicit input event so React onChange fires.
- `references/keys-ascii-vs-downup.md` — grapheme-aware key events, shift normalization tables, emoji→CHAR escape.
- `references/mouse-position-quads.md` — content-quads to viewport coordinates; clicks, drags, element screenshots.
- `references/window-scroll-gestures.md` — fuzzy window states with normalize-first ordering; synthesized scroll + sleep contract.
- `references/cloudflare-challenge-solver.md` — shadow-DOM challenge discovery and the 15%-from-left click policy.
- `references/fetch-interception-plane.md` — pause→inspect→continue/fulfill/fail lifecycle that must never stall.
- `references/tree-walk-shadow-piercing.md` — client-side traversal underpinning every finder (shadow roots first).
- `references/tab-storage-media-plane.md` — origin math for localStorage, download latching, capture family contracts.
- `references/stop-lifecycle-profile-cleanup.md` — converge-don't-raise shutdown ladder and temp-profile removal.

## Capsule map
- **Protocol core** — `transaction-generator-protocol`, `listener-idle-event-loop`, `domain-enable-reconciliation`, `oneshot-and-classfreeze`: the send/recv spine any CDP client needs.
- **Launch & config** — `config-args-pipeline`, `executable-discovery-shortest-wins`, `lazy-profile-and-root-sandbox`, `browser-start-connect-loop`.
- **Session & targets** — `target-inventory-events`, `cookie-jar-storage-plane`, `event-close-get-futures`, `stop-lifecycle-profile-cleanup`.
- **Query & elements** — `find-wait-retry-ladder`, `stale-node-retry-once`, `evaluate-js-dumps`, `element-attr-dual-plane`, `tree-walk-shadow-piercing`.
- **Input & automation** — `react-native-setter-inputs`, `keys-ascii-vs-downup`, `mouse-position-quads`, `window-scroll-gestures`.
- **Network & stealth** — `fetch-interception-plane`, `cloudflare-challenge-solver`, `tab-storage-media-plane`.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
zendriver (MPL-2.0), `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory project `ext-zendriver` (FULL mode, 4,120 nodes / 28,298 edges, generation 2026-08-23T12:07Z, head==base==origin at pass 1, parse_partial ×0, no stale twin). Pass-1 runner evidence: real Google Chrome 151 driven through `zd.start()` on-host (navigate/evaluate/select/clean-stop green); pytest fixture runs flapped only on the Arch `/bin/chromium` wrapper's slow startup racing the fixed retry budget — see `executable-discovery-shortest-wins` and `browser-start-connect-loop`. `zendriver/cdp/*` is generated from `scripts/generate_cdp.py` and intentionally not capsule-mined.

## Full view (memory graph)
Revalidate `ext-zendriver` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. BM25 note: query by symbol names (`Transaction`, `listener_loop`, `_normalise_key`) rather than prose; generated cdp-domain symbols crowd out core matches when domain words lead the query.

## Boundaries
Adopt the protocol/futures core, config pipeline, finder retry contracts, and input-injection invariants as portable behavior. Adapt executable discovery tables, timeouts/retry budgets, and stealth flag lists to your host and browser version. Omit the Cloudflare solver unless solving challenges is your use case, the generated `zendriver/cdp/` surface (regenerate it), examples/, docs/, and the mkdocs site.
