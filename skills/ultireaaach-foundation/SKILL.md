---
name: ultireaaach-foundation
description: Local-first LinkedIn lead collector kernel — loopback control plane with origin gating, SSRF-fenced rewrite proxy for framing foreign pages, vendored-SPA cloud mock (decodable fake JWT, envelope contracts, name-heuristic total defaults), guarded run FSM over SQLite runs, dedup-or-merge lead store, token-authenticated single-socket extension WS bridge. Load when porting local tool dashboards, browser-extension control planes, or offline-first collector stores.
---

# Ultireaaach: local LinkedIn lead-collector foundation

## Use this for
Use when porting a local-first control plane that drives a real browser via an unpacked extension, mocks a SaaS backend so a vendored SPA boots offline, or needs deterministic collect/merge storage with run lifecycle records. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/loopback-control-plane.md` — how does a privileged local API stay unreachable from non-loopback web origins while failing loud on port conflicts?
- `references/li-proxy-rewrite.md` — how do you iframe/proxy a hostile foreign page locally without tripping CORS or frame-busting, behind an SSRF fence?
- `references/lh-backend-cloud-mock.md` — what does it take to bootstrap a vendored SPA against a fake cloud backend (JWT shape, envelopes, persistence sidecar)?
- `references/smart-default-total-mock.md` — how can a mock answer EVERY unknown endpoint with a type-appropriate value instead of rejecting?
- `references/run-coordinator-fsm.md` — what guards keep a single-writer run lifecycle consistent across memory and SQLite?
- `references/lead-dedup-merge-store.md` — how do you dedupe leads by URL and merge without clobbering existing fields?
- `references/extension-bridge-bootstrap.md` — how does an unpacked MV3 extension discover and authenticate to a per-launch local service?
- `references/pas-launcher-rpc-shim.md` — how do you impersonate a desktop launcher's Socket.IO RPC surface so an Electron-targeted SPA boots locally?
- `references/mock-sidecar-restart-persistence.md` — where does mock state live so it survives restarts but stays out of the product database?
- `references/browser-electron-bridge-shim.md` — how does an Electron-renderer webapp run in a plain browser against local mocks without touching the bundle?
- `references/static-webdir-gate.md` — how do you serve a vendored SPA under mounted prefixes without feeding HTML to asset requests?

## Capsule map
- **Loopback control plane** — `loopback-control-plane`: 127.0.0.1-only binds + loopback-Origin gate on mutating methods + exit(1) port-conflict ladder.
- **SSRF-fenced rewrite proxy** — `li-proxy-rewrite`: LinkedIn-suffix allow-list, frame-header strip list, <base> + click-capture reinjection.
- **Cloud-API mock** — `lh-backend-cloud-mock`: decodable fake JWT payload contract, {data,count} envelopes, JSON sidecar persistence.
- **Total name-heuristic mock** — `smart-default-total-mock`: every unknown endpoint returns []/true/0/null/{ by name shape; duplicated deliberately in two shims with surface-specific list vocabularies.
- **Run FSM + durable counters** — `run-coordinator-fsm`: single-active-run, target bounds, guarded transitions, additive SQL counter deltas with terminal-state timestamps; restart amnesia is §12 spec law.
- **Dedup-or-merge lead store** — `lead-dedup-merge-store`: partial UNIQUE index identity, NULLIF/COALESCE field-fill merge, idempotent CSV source append.
- **Extension bridge bootstrap** — `extension-bridge-bootstrap`: bridge-info HTTP discovery -> ?token= WS auth -> 2s retry ladder; single socket slot.
- **PAS launcher-RPC shim** — `pas-launcher-rpc-shim`: rpc/ipc envelope duality (ack vs emit), mainWindow/__source routing ladder, requestActionAtLauncher responseEncoded wrap, second ungated HTTP plane on :4000.
- **Mock-sidecar restart persistence** — `mock-sidecar-restart-persistence`: JSON sidecar beside the DB, empty-catch fail-open load, log-and-swallow save, nextId continuity heuristic.
- **Browser-side Electron bridge shim** — `browser-electron-bridge-shim`: require-dispatch table, Proxy main window with client-side fixture table, cloud/LinkedIn fetch+XHR host rewriting, pre-bundle fake-JWT seeding.
- **Static web-dir gate** — `static-webdir-gate`: /member + /ui prefix strips, startsWith(webDir) defense-in-depth, two-condition SPA fallback (HTML navigation AND extension-less).

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Ultireaaach (private workspace, node >=22 / TypeScript), `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory project `ultireaaach` (FULL mode, gen 2026-08-23T00:33:18Z, 20841 nodes / 113379 edges, ready; parse-partial limited to build CSS chunks + lockfile).

## Full view (memory graph)
Revalidate `ultireaaach` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: loopback binding + origin gate, proxy header-strip list and host fence, JWT payload-shape thinking, guarded FSM transitions, dedup-identity merge SQL. Adapt the LinkedHelper-specific endpoint vocabulary and PAS RPC names to your own SPA's surface. Omit the vendored dashboard bundle and systeminformation library entirely (read-only assets), and the LH-specific license/machine fixtures.
