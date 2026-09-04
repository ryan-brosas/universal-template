<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Browser Harness Foundation

## Use this for
Browser automation tooling that must attach to a real (already-open) browser over the DevTools protocol, offer high-level imperative page helpers, record user actions, and compose verified videos from those recordings. Also covers the portable infra around any helper daemon: platform-branched IPC auth, PID-reuse-safe process control, self-healing startup, opt-out telemetry, and dual-audience CLI auth. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./ipc-token-loopback-boundary.md` — AF_UNIX+umask-0600 vs TCP-loopback+bearer-token transport; every request carries the token on Windows.
- `./ipc-endpoint-security.md` — endpoint enumeration across isolated/shared runtime dirs; handshake liveness beats bare connect.
- `./ipc-detached-spawn-contract.md` — platform detach flags (no DETACHED_PROCESS on Windows) + newline-framed one-shot JSON RPC with central token injection.
- `./daemon-ping-identity-defense.md` — pong-shape liveness + bool-rejecting PID validation.
- `./daemon-restart-identity-ladder.md` — graceful-shutdown → poll → identity-recheck → SIGTERM, never kill-by-pid-file.
- `./admin-selfheal-ladder.md` — log-tail classification → one-shot recoveries → errors-as-instructions.
- `./cloud-provision-compensation.md` — create-before-attach + BaseException-wide stop of billed cloud browsers.
- `./cloud-bootstrap-precedence.md` — five-gate opt-in auto-spawn; explicit endpoints veto billing.
- `./update-flow-version-cache.md` — 24h PyPI cache + pre-release-aware tuples + banner-once-per-day.
- `./browser-launch-spec-table.md` — consent-preferred base selection + profile-tail launch table.
- `./doctor-snap-contract.md` — two-signal core health + evidence-preserving snap probes.
- `./admin-json-health-plane.md` — fail-closed Target.getTargets health probe + stable JSON doctor report + BH_REQUIRE_EXISTING_DAEMON exec veto.
- `./macos-consent-click-ladder.md` — no-activate AXPress walk with a six-status tuple contract.
- `./daemon-toggle-state-tri-state.md` — Local State consent tri-state (True/False/None) + file-plus-socket port-liveness anti-stale check.
- `./daemon-log-endpoint-redaction.md` — write-time scheme://host[:port] reduction of credentialed CDP URLs; fail-closed placeholder.
- `./paths-env-layout.md` — create-only chmod dirs + setdefault-only .env layering (real env wins).
- `./daemon-ws-discovery-ladder.md` — env override → profile scan w/ liveness → /json/version → fixed-port probes.
- `./daemon-patient-handshake.md` — 45s WS opening handshake for human-speed consent popups.
- `./daemon-named-dedicated-tab.md` — per-client dedicated tab + five-rung page-reuse ladder.
- `./daemon-stale-session-chain-map.md` — chain-preserving redirect; explicit-session never redirected.
- `./daemon-target-browser-scope-rule.md` — Target.* calls forced session-less; current_tab identity resolved server-side (issue #304).
- `./daemon-set-session-parallel-budget.md` — parallel old-teardown ∥ new-enables under a 5s IPC timeout.
- `./daemon-event-tap-monkeypatch.md` — handle_event wrapper: ring buffer + dialog latch + fire-and-forget effects.
- `./daemon-entry-lifecycle.md` — ping-guarded idempotent startup, per-boot log truncation, guaranteed teardown.
- `./daemon-shutdown-recovery-barrier.md` — barrier→cancel+drain→cleanup ordering; failed cleanup rolls back so the daemon stays a retryable billing authority.
- `./helper-js-eval-layer.md` — unserializable decode + conditional return-wrapper retry.
- `./helper-ipc-response-timeout-budget.md` — per-call response budgets over a short connect timeout; typed _IPCResponseTimeout; 60s screenshot tolerance.
- `./helper-framework-input-fill.md` — rawKeyDown select-all + synthetic input/change for controlled inputs.
- `./helper-cdp-input-dispatch.md` — raw Input-domain click/key/wheel/upload dispatch; char-event gating under Alt/Ctrl/Meta; BH_DEBUG_CLICKS overlay.
- `./helper-spa-wait-ladder.md` — readyState / checkVisibility / session-scoped network-idle waits.
- `./helper-tab-attach-vs-activate.md` — attach ≠ activate; blank-then-navigate.
- `./helper-trace-telemetry.md` — post-import globals() wrapping + stream tails for agent-facing REPLs.
- `./helper-sharp-edges.md` — dialog short-circuit in page_info, LLM-size screenshot clamp, key-gated http proxy.
- `./agent-helper-extension.md` — bottom-import cycle-break + workspace helper merge.
- `./recorder-folder-marker-whitelist.md` — folder + marker + ACTIONS whitelist; never-raise observe.
- `./recorder-auto-rollover.md` — activity-mtime idle rollover; explicit recordings never auto-roll.
- `./recorder-redaction-at-write.md` — URL-key-preserving scrub + password mask + sensitive-regex net.
- `./recorder-action-details-projection.md` — per-helper allowlist projection + generation-time password masking with length preservation.
- `./video-brief-validation.md` — reject-unknown + typed validators + identity-leak bans + budget gate.
- `./video-summary-projection.md` — sanitized summary + sourceLine-keyed reveal ledger; passwords have NO reveal path.
- `./video-action-beat-compilation.md` — per-action compile gates: viewport match, semantic-route ban, ledger-gated text reveal, cameraCut threshold.
- `./video-cadence-budget-gates.md` — sticky narration as an ERROR + word-count pacing + capped hard duration budget.
- `./video-integrity-gates.md` — manifest→review→recompute-equality gating before MP4 export.
- `./video-browser-review-harness.md` — serve + subprocess-drive + sentinel-line result protocol.
- `./video-render-preflight-ladder.md` — runtime accumulate-all-errors preflight + hard export gate; invalid compositions are unrenderable.
- `./video-click-safe-camera.md` — largest-safe-zoom binary search + compile-time click-visibility ledger.
- `./cloud-zombie-reaper.md` — billed-session cleanup: finishedAt-liveness pagination, Z-swap timestamps, per-item failure isolation.
- `./admin-cloud-profile-plane.md` — pageSize-capped pagination with totalItems early-stop, raise-don't-guess name→id resolution, profile-use sync shell-out.
- `./dev-launcher-env-namespacing.md` — path-cksum /tmp namespacing + BU_NAME gate + three-tier interpreter exec ladder.
- `./video-mask-raster-plane.md` — offline PIL rasterization of the same opaque redaction rects the live canvas draws; review certifies shipped pixels.
- `./video-export-choreography.md` — remember-tab → arm CDP downloads → size-stable poll → fail-closed download-behavior restore in finally.
- `./domain-skill-exemplar-extractor.md` — env-driven site script contract: one js() JSON round-trip, error-dict exits, slug-named file pair.
- `./auth-cli-dual-audience.md` — PKCE/device/manual login, JSON-for-agent + prose-for-human.
- `./auth-private-storage-lifecycle.md` — 0600-born atomic auth.json writes, namespaced clear with last-key-out unlink, corrupt-file fail-loud.
- `./telemetry-detached-optout.md` — detached sender + key-name allowlist + URL redaction.
- `./telemetry-browser-kind-self-report.md` — daemon-side env derivation piggybacked on ping; whitelist-or-None consumers; exactly one telemetry event per exit path.

## Capsule map
- **IPC & identity** — `ipc-token-loopback-boundary`, `ipc-endpoint-security`, `daemon-ping-identity-defense`, `ipc-detached-spawn-contract`: platform-branched socket auth, multi-instance discovery, pong+validated-PID liveness surviving stale endpoints and PID reuse, true daemon detachment + newline-framed one-shot RPC.
- **Admin & lifecycle** — `daemon-restart-identity-ladder`, `admin-selfheal-ladder`, `cloud-provision-compensation`, `cloud-bootstrap-precedence`, `update-flow-version-cache`, `admin-cloud-profile-plane`, `admin-json-health-plane`: PID-safe supervision, log-classified self-healing with kind-keyed stale disposition, billing compensation, opt-in bootstrap precedence, cached + kill-switchable update flow, capped-pagination + fail-loud cloud-profile management, fail-closed orchestrator health JSON.
- **Browser discovery & consent** — `browser-launch-spec-table`, `doctor-snap-contract`, `macos-consent-click-ladder`, `paths-env-layout`, `daemon-ws-discovery-ladder`, `daemon-patient-handshake`: finding/launching/healing the right browser across Chrome 136/144/147 permission regimes.
- **CDP attach & session** — `daemon-named-dedicated-tab`, `daemon-stale-session-chain-map`, `daemon-target-browser-scope-rule`, `daemon-set-session-parallel-budget`, `daemon-event-tap-monkeypatch`, `daemon-entry-lifecycle`, `daemon-shutdown-recovery-barrier`, `daemon-log-endpoint-redaction`: dedicated tabs, chain-preserving recovery, browser-level dispatch scoping, parallel re-arming under client timeouts, event tap, process lifecycle, fail-closed shutdown with retryable billing cleanup, credential-free connect logs.
- **Helpers** — `helper-js-eval-layer`, `helper-ipc-response-timeout-budget`, `helper-framework-input-fill`, `helper-spa-wait-ladder`, `helper-tab-attach-vs-activate`, `helper-trace-telemetry`, `helper-sharp-edges`, `agent-helper-extension`: js() contract, per-call response budgets, framework-aware fill, three SPA waits, attach-vs-activate split, runner-side tracing, surprising return shapes, user extensibility.
- **Recorder** — `recorder-folder-marker-whitelist`, `recorder-auto-rollover`, `recorder-redaction-at-write`: cross-process marker state, activity-based rollover, generation-time redaction.
- **Video** — `video-brief-validation`, `video-summary-projection`, `video-action-beat-compilation`, `video-cadence-budget-gates`, `video-integrity-gates`, `video-browser-review-harness`, `video-render-preflight-ladder`, `video-click-safe-camera`, `video-mask-raster-plane`, `video-export-choreography`: reject-don't-ignore brief validation, sanitized summary with a sourceLine-keyed reveal ledger, per-action compile gates for privacy and watchability, sticky-narration + hard-budget compile gates, hash-pinned review/export gates, sentinel-line browser harness, runtime accumulate-all-errors preflight gating export, click-safe camera framing that never hides the action, pixel-faithful offline mask rasterization for human review, and fail-closed CDP export choreography.
- **Launcher & extensibility** — `dev-launcher-env-namespacing`, `domain-skill-exemplar-extractor`: dev-mode multi-instance namespacing ahead of any Python import, and the env-driven site-script contract taught by one decisive exemplar.
- **Auth & telemetry** — `auth-cli-dual-audience`, `telemetry-detached-optout`, `telemetry-browser-kind-self-report`: three-path CLI auth with dual-format output; detached, key-name-allowlisted, opt-out telemetry attributed by daemon-self-reported browser kind.
- **Cloud ops** — `cloud-zombie-reaper`: REST reaper for leaked billed sessions (liveness-by-absent-field pagination, string-typed costs).
- **Auth private-storage lifecycle** — `auth-private-storage-lifecycle`: how do you store an API key on disk so it is never world-readable, never half-written, and never silently ignored.
- **Remote-debugging consent tri-state** — `daemon-toggle-state-tri-state`: how do you decide "is remote debugging on?" when Chrome's answer can be missing, stale, or a lie.
- **CDP input-dispatch primitives** — `helper-cdp-input-dispatch`: how do you synthesize trusted mouse/key/wheel/file input over raw DevTools, and when does each escape hatch fire.
- **Recorder action-details projection** — `recorder-action-details-projection`: how do you record WHAT an agent did without recording the secrets it typed.
## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
browser-harness (MIT), `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory project `browser-harness` (`$REFERENCE_ROOT/browser-harness`, live checkout), full mode, 2,699 nodes / 5,043 edges, head==base==pin re-verified 2026-08-26 pass 9 after a FULL re-index of the 21-commit drift wave (+582/−79). All cited source/test paths returned `no_recorded_issue` + `metadata_match` via check_index_coverage (generation 2026-08-26T11:06:55Z). Legacy 4-ref leaf fully swept to capsule-v2 (2026-08-23 frontier-agents lane pass 1). Passes 5–8 (2026-08-25/26, FAC-29 miner-browser-harness): six deep-learning capsules, video-beat capsule, browser-kind chain, Target.* scope rule, plus three independent uncited-seam censuses — those capsules were lost from disk in a leaf regression and were RESTORED at this pin during pass 9 from fresh source evidence. Pass 9 (2026-08-26): pin advance + drift-wave mining — shutdown/recovery barrier, JSON health plane, log-endpoint redaction, IPC response budgets, extends to cloud/update/selfheal capsules; upstream added direct unit tests for several previously caveat-marked seams (executed GREEN ambient).

## Full view (memory graph)
Revalidate `browser-harness` before porting: run `index_status --project browser-harness --verbose`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record root, branch, commit, mode, node/edge counts, freshness, and coverage caveats; source and direct tests decide shipped claims. Direct-test density is highest on admin lifecycle + orchestrator health (test_admin.py), IPC payloads (test_ipc.py), session/set_session/shutdown/recovery semantics (test_daemon.py), waits/fill/js/timeout budgets (test_helpers.py, test_run.py CLI grammar); recorder/video/auth modules and the live-Chrome discovery ladder/patient handshake carry in-capsule deterministic-anchor caveats where no suite exists.

## Boundaries
Adopt the daemon lifecycle, helper API, recorder, video-composition contracts, and the IPC/auth/telemetry plumbing; adapt CDP transport details, video encoders, Browser Use cloud specifics, and BH_*/BU_* env names; omit domain-skills content (~100 site-specific markdown files), the interaction-skills docs corpus, and claude-plugin packaging unless porting the whole product shape. The two Python domain-skills utilities are mined as pattern exemplars (`domain-skill-exemplar-extractor`, `cloud-zombie-reaper`), not product surface. Coverage caveats are recorded in-capsule where a seam has no direct upstream unit test (Windows token path, live-Chrome discovery ladder, patient handshake, tracer, recorder/telemetry/auth/video internals, root bash launcher).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`admin-cloud-profile-plane.md`](./admin-cloud-profile-plane.md)
- [`admin-json-health-plane.md`](./admin-json-health-plane.md)
- [`admin-selfheal-ladder.md`](./admin-selfheal-ladder.md)
- [`agent-helper-extension.md`](./agent-helper-extension.md)
- [`auth-cli-dual-audience.md`](./auth-cli-dual-audience.md)
- [`auth-private-storage-lifecycle.md`](./auth-private-storage-lifecycle.md)
- [`browser-launch-spec-table.md`](./browser-launch-spec-table.md)
- [`cloud-bootstrap-precedence.md`](./cloud-bootstrap-precedence.md)
- [`cloud-provision-compensation.md`](./cloud-provision-compensation.md)
- [`cloud-zombie-reaper.md`](./cloud-zombie-reaper.md)
- [`daemon-entry-lifecycle.md`](./daemon-entry-lifecycle.md)
- [`daemon-event-tap-monkeypatch.md`](./daemon-event-tap-monkeypatch.md)
- [`daemon-log-endpoint-redaction.md`](./daemon-log-endpoint-redaction.md)
- [`daemon-named-dedicated-tab.md`](./daemon-named-dedicated-tab.md)
- [`daemon-patient-handshake.md`](./daemon-patient-handshake.md)
- [`daemon-ping-identity-defense.md`](./daemon-ping-identity-defense.md)
- [`daemon-restart-identity-ladder.md`](./daemon-restart-identity-ladder.md)
- [`daemon-set-session-parallel-budget.md`](./daemon-set-session-parallel-budget.md)
- [`daemon-shutdown-recovery-barrier.md`](./daemon-shutdown-recovery-barrier.md)
- [`daemon-stale-session-chain-map.md`](./daemon-stale-session-chain-map.md)
- [`daemon-target-browser-scope-rule.md`](./daemon-target-browser-scope-rule.md)
- [`daemon-toggle-state-tri-state.md`](./daemon-toggle-state-tri-state.md)
- [`daemon-ws-discovery-ladder.md`](./daemon-ws-discovery-ladder.md)
- [`dev-launcher-env-namespacing.md`](./dev-launcher-env-namespacing.md)
- [`doctor-snap-contract.md`](./doctor-snap-contract.md)
- [`domain-skill-exemplar-extractor.md`](./domain-skill-exemplar-extractor.md)
- [`helper-cdp-input-dispatch.md`](./helper-cdp-input-dispatch.md)
- [`helper-framework-input-fill.md`](./helper-framework-input-fill.md)
- [`helper-ipc-response-timeout-budget.md`](./helper-ipc-response-timeout-budget.md)
- [`helper-js-eval-layer.md`](./helper-js-eval-layer.md)
- [`helper-sharp-edges.md`](./helper-sharp-edges.md)
- [`helper-spa-wait-ladder.md`](./helper-spa-wait-ladder.md)
- [`helper-tab-attach-vs-activate.md`](./helper-tab-attach-vs-activate.md)
- [`helper-trace-telemetry.md`](./helper-trace-telemetry.md)
- [`ipc-detached-spawn-contract.md`](./ipc-detached-spawn-contract.md)
- [`ipc-endpoint-security.md`](./ipc-endpoint-security.md)
- [`ipc-token-loopback-boundary.md`](./ipc-token-loopback-boundary.md)
- [`macos-consent-click-ladder.md`](./macos-consent-click-ladder.md)
- [`paths-env-layout.md`](./paths-env-layout.md)
- [`recorder-action-details-projection.md`](./recorder-action-details-projection.md)
- [`recorder-auto-rollover.md`](./recorder-auto-rollover.md)
- [`recorder-folder-marker-whitelist.md`](./recorder-folder-marker-whitelist.md)
- [`recorder-redaction-at-write.md`](./recorder-redaction-at-write.md)
- [`telemetry-browser-kind-self-report.md`](./telemetry-browser-kind-self-report.md)
- [`telemetry-detached-optout.md`](./telemetry-detached-optout.md)
- [`update-flow-version-cache.md`](./update-flow-version-cache.md)
- [`video-action-beat-compilation.md`](./video-action-beat-compilation.md)
- [`video-brief-validation.md`](./video-brief-validation.md)
- [`video-browser-review-harness.md`](./video-browser-review-harness.md)
- [`video-cadence-budget-gates.md`](./video-cadence-budget-gates.md)
- [`video-click-safe-camera.md`](./video-click-safe-camera.md)
- [`video-export-choreography.md`](./video-export-choreography.md)
- [`video-integrity-gates.md`](./video-integrity-gates.md)
- [`video-mask-raster-plane.md`](./video-mask-raster-plane.md)
- [`video-render-preflight-ladder.md`](./video-render-preflight-ladder.md)
- [`video-summary-projection.md`](./video-summary-projection.md)
