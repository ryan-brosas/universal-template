---
name: linkedin-mcp-foundation
description: "Use when building a browser-automation MCP server over one logged-in profile: session-state persistence, multi-process daemon ownership (lock/lease/election), descriptor trust, container preflights, auth repair ladders, idle handoff, and tool serialization."
disable-model-invocation: true
---
# LinkedIn MCP Foundation

## Use this for
Build a browser-automation or MCP server over a logged-in browser profile: persistent session state with rotation/quarantine/restore, cross-platform runtime reuse, two-granularity ownership (process lock + refcounted lease), detached owner election with version-skew stand-down, loopback-checked descriptor trust, container mount preflights, stealth windowless targets, two-layer tool serialization, plus the auth-repair and lifecycle planes: login claim ladders, quiescence latches, idle-handoff polling, checkpoint-restart bridges, credential import with rotate-validate-commit, and reference normalization. Source and its direct tests (60+ test files) are the contract; references carry decisive excerpts and retrieval.

## Load the matching source dump
- `references/session-artifact-layout.md` — the four artifacts per login, derived per-runtime profiles, deterministic runtime ids, `login_generation` stamping.
- `references/canonical-path-pairing.md` — why `expanduser().resolve()` must be ONE named function used everywhere.
- `references/config-precedence-ladder.md` — defaults→env→args→validate ladder; exposure-based proxy-secret policy; MCPB placeholder gate.
- `references/container-detection.md` — only signals describing OUR process count; segment matching; measured post-mortems; env override.
- `references/session-rotation.md` — move-not-delete quarantine, atomic restore, tri-state peer guard, cancel-deferral around the move.
- `references/chromium-lock-attribution.md` — SingletonLock host-gated pid probing; three-signal exclusivity.
- `references/lock-vs-lease.md` — process-lifetime lock vs reference-counted lease; POSIX-only handover; fork reset.
- `references/owner-election.md` — three-state Reach probing, version-skew stand-down ladder, platform-split election.
- `references/descriptor-trust.md` — loopback-checked discovery, keyed config fingerprint, instance-named tokens.
- `references/server-role-and-liveness.md` — role-as-process-state without import cycles; heartbeat-driven call cancellation.
- `references/daemon-proxy-owner-recovery.md` — per-operation client factory over a replaceable owner; boundary-classified failures; replay only what is provably safe.
- `references/browser-manager-lifecycle.md` — one funnel that refuses identity overrides, refuses downgrades pre-mutation, and gates profile handover on confirmed close.
- `references/login-viewer-preflight.md` — mount/writability refusals that name their remedy; token-private noVNC stack; reverse teardown.
- `references/dll-diagnosis-middleware.md` — translating native-extension failures into actionable errors without misclassification.
- `references/windowless-target.md` — stealth without headless announcement; measured platform support only; refuse-don't-degrade.
- `references/launch-options-builder.md` — ONE pure builder so login and scraping mint sessions in the same binary; conditional capability switches carry their measurements.
- `references/browser-downgrade-guard.md` — fail-open downgrade detection whose evidence is consumed by the first miss.
- `references/private-state-hardening.md` — harden-then-verify file modes + extended-ACL stripping for credentials.
- `references/two-layer-serialization.md` — asyncio.Lock inside the process, profile lease across processes, ToolError discipline in middleware.
- `references/update-check-notice.md` — additive-content version notices that can never break or delay a tool call.
- `references/idle-handoff-poll-loop.md` — background poll closing an idle browser without killing in-flight calls; in-coroutine recheck; min-hold window.
- `references/checkpoint-restart-bridge.md` — derive-a-runtime-session pipeline: validate → checkpoint → restart → revalidate → commit ordering.
- `references/lease-object-settle.md` — keep-the-acquired-object teardown settle; cancel-deferring shield loop; err-toward-hold on unconfirmed shutdown.
- `references/feed-auth-proxy-triage.md` — four-way classification of validator failures so a proxy fault never retires a valid session.
- `references/authentication-source-gate.md` — all-artifacts-or-remedy startup gate for a multi-file credential store.
- `references/auth-marker-replay-budget.md` — owner→frontend auth markers as error RESULTS that survive masking; started-logins waited out; read-only-only replays inside the remaining budget.
- `references/auth-quiescence-latch.md` — two-field latch stopping an owner from re-opening a dead session while a peer signs in.
- `references/login-claim-ladder.md` — task-sharing claim ladder for concurrent pollers; UNGUARDED sentinel generation guards; auto-import guard rails.
- `references/import-rotate-validate-commit.md` — cheapest-first credential triage; rotation before validation; restore-on-failure bookkeeping.
- `references/reference-normalization-gate.md` — parse-or-refuse identifier normalization; traversal-proof escaping; slugged numeric ids.
- `references/rail-pick-scroll-engine.md` — content-scored container picking; growth-stall termination; caller-budget derivation.
- `references/locale-proof-picker-detection.md` — structural-before-textual barrier detection layering.
- `references/error-diagnostics-carve-out.md` — class-keyed error decoration: corrections verbatim, defects with diagnostics.
- `references/stand-down-turnover.md` — in-route token check, one-place shutdown noticing, bounded waits with hard-exit backstop.

## Capsule map
- **Session state** — `session-artifact-layout`: four artifacts + runtime derivation. `canonical-path-pairing`: expand+resolve pairing invariant. `container-detection`: signal epistemology for env heuristics. `session-rotation`: quarantine/restore/peer-guard ladder. `chromium-lock-attribution`: foreign-vs-stale lock attribution.
- **Ownership & trust** — `lock-vs-lease`: two ownership lifetimes + fork reset. `owner-election`: detached-owner election + stale-owner stand-down. `descriptor-trust`: loopback gating + keyed fingerprints. `server-role-and-liveness`: role-as-process-state + heartbeat cancellation. `daemon-proxy-owner-recovery`: forwarding that survives owner replacement without replaying mutations. `browser-manager-lifecycle`: funnel refusals + confirmed-close profile handover gate.
- **Browser ops** — `launch-options-builder`: one pure builder so login/scrape binaries cannot drift. `windowless-target`: no-window/no-headless-flag stealth. `browser-downgrade-guard`: fail-open profile-version guard. `two-layer-serialization`: session×process tool serialization. `idle-handoff-poll-loop`: prompt release of an idle shared browser. `checkpoint-restart-bridge`: derived-runtime session commit ordering. `lease-object-settle`: unconfirmed-shutdown settle semantics.
- **Auth repair** — `feed-auth-proxy-triage`: proxy-fault vs dead-session classification. `auth-quiescence-latch`: owner stops re-opening broken sessions. `login-claim-ladder`: concurrent pollers share one login/import. `import-rotate-validate-commit`: foreign-credential adoption without data loss. `auth-marker-replay-budget`: cross-hop marker results + budgeted read-only replays. `authentication-source-gate`: all-artifacts-or-remedy startup gate.
- **Scraping safety** — `reference-normalization-gate`: identifiers before URL interpolation. `rail-pick-scroll-engine`: unknown-container scroll exhaustion under a caller budget. `locale-proof-picker-detection`: structural interstitial checks ahead of word tables.
- **Configuration** — `config-precedence-ladder`: defaults→env→args ladder with exposure-based secret policy.
- **Environment & UX** — `login-viewer-preflight`: remedy-naming mount preflight + supervised VNC stack. `dll-diagnosis-middleware`: VC++ runtime failure translation. `private-state-hardening`: credential file hardening. `update-check-notice`: non-breaking update nudges. `error-diagnostics-carve-out`: corrections vs issue diagnostics. `stand-down-turnover`: authenticated graceful daemon turnover.

## Extending the foundation
Add one `references/<seam>.md` capsule-v2 file per graph-selected, source-confirmed porting question: marker line 1, Source/Question header, Path/Symbol, Signature, Data Shape, decisive excerpt, Flow, Invariant, direct-test Probe, `search_graph` Retrieve, Verdict. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
linkedin-mcp-server (Apache-2.0), `main@0cd1e5fb` (2026-08-23; advanced pass 2 from `cfcd9c9a`, origin-fetched 20 commits, code drift incl. new `scraping/identifiers.py`); Codebase Memory project `linkedin-mcp-server` (`/mnt/hdd/utopia/inspo/linkedin-mcp-server`, canonical `/mnt/hdd/utopia/inspo/linkedin/linkedin-mcp-server`; LIVE-SYMLINK benign twin class — old root resolves into the real tree; 4,567 nodes / 24,647 edges at the new pin, full mode, ready; content-freshness proven via drift-introduced symbol `_decoded` resolving :140-153; parse_partial ×2 = docker-entrypoint.sh + pytest.ini only). Pass 1 legacy sweep [DONE:89]: 3 prose refs rewritten into 16 capsule-v2 refs. Pass 2 [DONE:354]: +12 capsules from whole-file reads of `drivers/browser.py` (1,122L), `bootstrap.py` auth plane (:1531-2260), `daemon_owner.py` (842L), `browser_import/orchestrate.py` (368L), `scraping/identifiers.py`, `core/utils.py` rail engine, `core/auth.py` picker detection; existing 16 re-checked against the diff — none contradicted. Pass 3 [DONE:2026-08-25] at the same pin (re-mined, graph re-verified 4,567 nodes / 24,647 edges): +6 capsules from whole-file reads of `config/loaders.py` (882L), `daemon_proxy.py` (808L), `daemon_auth.py` (450L), `core/browser.py` (720L), `browser_launch.py`, `authentication.py` — total 34 capsule-v2 refs; work record created at inspo/linkedin-mcp-server-work/ this pass.

## Full view (memory graph)
Revalidate `linkedin-mcp-server` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, `get_code_snippet`. Record root, branch, commit, mode, node/edge counts, freshness, coverage caveats; source and direct tests decide shipped claims. Key traces: `rotate_source_profile` ↔ `a_peer_already_signed_in` (peer-guard flow); `ProfileLease.try_acquire` inbound from `SequentialToolExecutionMiddleware.on_call_tool` + `drivers/browser.py` (three-signal exclusivity consumers); `close_browser` ← `release_profile_if_idle_or_requested` / `invalidate_auth_and_trigger_relogin` / stand-down lifespan; `interactive_login(superseded_by=...)` ← `_run_login_flow` reading `_state.login_supersedes`.

## Boundaries
Adopt session artifact layout, rotation/restore discipline, lock/lease ownership split, election + descriptor trust, role model, preflights, serialization patterns, auth-repair ladders, import commit ordering, and normalization gates. Adapt paths, budgets, platform ACL internals, and VNC specifics. Omit LinkedIn scraping flows (covered by `linkedin-scrapers-combined`), the extractor's DOM grammar beyond cited seams, cookie AES internals (`extract.py`), per-browser discovery tables (`discovery.py`), and Docker image build details unless a target requires them.
