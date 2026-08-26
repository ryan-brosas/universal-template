---
name: browser-harness-foundation
description: "Use when building browser automation tooling: a CDP daemon that attaches to a real browser, high-level page helpers, action recording, and video composition — plus the IPC/auth/telemetry/self-heal plumbing around such a daemon."
disable-model-invocation: true
---
# Browser Harness Foundation

## Use this for
Browser automation tooling that must attach to a real (already-open) browser over the DevTools protocol, offer high-level imperative page helpers, record user actions, and compose verified videos from those recordings. Also covers the portable infra around any helper daemon: platform-branched IPC auth, PID-reuse-safe process control, self-healing startup, opt-out telemetry, and dual-audience CLI auth. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/ipc-token-loopback-boundary.md` — AF_UNIX+umask-0600 vs TCP-loopback+bearer-token transport; every request carries the token on Windows.
- `references/ipc-endpoint-security.md` — endpoint enumeration across isolated/shared runtime dirs; handshake liveness beats bare connect.
- `references/ipc-detached-spawn-contract.md` — platform detach flags (no DETACHED_PROCESS on Windows) + newline-framed one-shot JSON RPC with central token injection.
- `references/daemon-ping-identity-defense.md` — pong-shape liveness + bool-rejecting PID validation.
- `references/daemon-restart-identity-ladder.md` — graceful-shutdown → poll → identity-recheck → SIGTERM, never kill-by-pid-file.
- `references/admin-selfheal-ladder.md` — log-tail classification → one-shot recoveries → errors-as-instructions.
- `references/cloud-provision-compensation.md` — create-before-attach + BaseException-wide stop of billed cloud browsers.
- `references/cloud-bootstrap-precedence.md` — five-gate opt-in auto-spawn; explicit endpoints veto billing.
- `references/update-flow-version-cache.md` — 24h PyPI cache + pre-release-aware tuples + banner-once-per-day.
- `references/browser-launch-spec-table.md` — consent-preferred base selection + profile-tail launch table.
- `references/doctor-snap-contract.md` — two-signal core health + evidence-preserving snap probes.
- `references/macos-consent-click-ladder.md` — no-activate AXPress walk with a six-status tuple contract.
- `references/daemon-toggle-state-tri-state.md` — Local State consent tri-state (True/False/None) + file-plus-socket port-liveness anti-stale check.
- `references/paths-env-layout.md` — create-only chmod dirs + setdefault-only .env layering (real env wins).
- `references/daemon-ws-discovery-ladder.md` — env override → profile scan w/ liveness → /json/version → fixed-port probes.
- `references/daemon-patient-handshake.md` — 45s WS opening handshake for human-speed consent popups.
- `references/daemon-named-dedicated-tab.md` — per-client dedicated tab + five-rung page-reuse ladder.
- `references/daemon-stale-session-chain-map.md` — chain-preserving redirect; explicit-session never redirected.
- `references/daemon-set-session-parallel-budget.md` — parallel old-teardown ∥ new-enables under a 5s IPC timeout.
- `references/daemon-event-tap-monkeypatch.md` — handle_event wrapper: ring buffer + dialog latch + fire-and-forget effects.
- `references/daemon-entry-lifecycle.md` — ping-guarded idempotent startup, per-boot log truncation, guaranteed teardown.
- `references/helper-js-eval-layer.md` — unserializable decode + conditional return-wrapper retry.
- `references/helper-framework-input-fill.md` — rawKeyDown select-all + synthetic input/change for controlled inputs.
- `references/helper-cdp-input-dispatch.md` — raw Input-domain click/key/wheel/upload dispatch; char-event gating under Alt/Ctrl/Meta; BH_DEBUG_CLICKS overlay.
- `references/helper-spa-wait-ladder.md` — readyState / checkVisibility / session-scoped network-idle waits.
- `references/helper-tab-attach-vs-activate.md` — attach ≠ activate; blank-then-navigate.
- `references/helper-trace-telemetry.md` — post-import globals() wrapping + stream tails for agent-facing REPLs.
- `references/helper-sharp-edges.md` — dialog short-circuit in page_info, LLM-size screenshot clamp, key-gated http proxy.
- `references/agent-helper-extension.md` — bottom-import cycle-break + workspace helper merge.
- `references/recorder-folder-marker-whitelist.md` — folder + marker + ACTIONS whitelist; never-raise observe.
- `references/recorder-auto-rollover.md` — activity-mtime idle rollover; explicit recordings never auto-roll.
- `references/recorder-redaction-at-write.md` — URL-key-preserving scrub + password mask + sensitive-regex net.
- `references/recorder-action-details-projection.md` — per-helper allowlist projection + generation-time password masking with length preservation.
- `references/video-brief-validation.md` — reject-unknown + typed validators + identity-leak bans + budget gate.
- `references/video-summary-projection.md` — sanitized summary + sourceLine-keyed reveal ledger; passwords have NO reveal path.
- `references/video-cadence-budget-gates.md` — sticky narration as an ERROR + word-count pacing + capped hard duration budget.
- `references/video-integrity-gates.md` — manifest→review→recompute-equality gating before MP4 export.
- `references/video-browser-review-harness.md` — serve + subprocess-drive + sentinel-line result protocol.
- `references/video-render-preflight-ladder.md` — runtime accumulate-all-errors preflight + hard export gate; invalid compositions are unrenderable.
- `references/video-click-safe-camera.md` — largest-safe-zoom binary search + compile-time click-visibility ledger.
- `references/cloud-zombie-reaper.md` — billed-session cleanup: finishedAt-liveness pagination, Z-swap timestamps, per-item failure isolation.
- `references/admin-cloud-profile-plane.md` — pageSize-capped pagination with totalItems early-stop, raise-don't-guess name→id resolution, profile-use sync shell-out.
- `references/dev-launcher-env-namespacing.md` — path-cksum /tmp namespacing + BU_NAME gate + three-tier interpreter exec ladder.
- `references/video-mask-raster-plane.md` — offline PIL rasterization of the same opaque redaction rects the live canvas draws; review certifies shipped pixels.
- `references/video-export-choreography.md` — remember-tab → arm CDP downloads → size-stable poll → fail-closed download-behavior restore in finally.
- `references/domain-skill-exemplar-extractor.md` — env-driven site script contract: one js() JSON round-trip, error-dict exits, slug-named file pair.
- `references/auth-cli-dual-audience.md` — PKCE/device/manual login, JSON-for-agent + prose-for-human.
- `references/auth-private-storage-lifecycle.md` — 0600-born atomic auth.json writes, namespaced clear with last-key-out unlink, corrupt-file fail-loud.
- `references/telemetry-detached-optout.md` — detached sender + key-name allowlist + URL redaction.

## Capsule map
- **IPC & identity** — `ipc-token-loopback-boundary`, `ipc-endpoint-security`, `daemon-ping-identity-defense`, `ipc-detached-spawn-contract`: platform-branched socket auth, multi-instance discovery, pong+validated-PID liveness surviving stale endpoints and PID reuse, true daemon detachment + newline-framed one-shot RPC.
- **Admin & lifecycle** — `daemon-restart-identity-ladder`, `admin-selfheal-ladder`, `cloud-provision-compensation`, `cloud-bootstrap-precedence`, `update-flow-version-cache`, `admin-cloud-profile-plane`: PID-safe supervision, log-classified self-healing, billing compensation, opt-in bootstrap precedence, cached update flow, capped-pagination + fail-loud cloud-profile management.
- **Browser discovery & consent** — `browser-launch-spec-table`, `doctor-snap-contract`, `macos-consent-click-ladder`, `paths-env-layout`, `daemon-ws-discovery-ladder`, `daemon-patient-handshake`: finding/launching/healing the right browser across Chrome 136/144/147 permission regimes.
- **CDP attach & session** — `daemon-named-dedicated-tab`, `daemon-stale-session-chain-map`, `daemon-set-session-parallel-budget`, `daemon-event-tap-monkeypatch`, `daemon-entry-lifecycle`: dedicated tabs, chain-preserving recovery, parallel re-arming under client timeouts, event tap, process lifecycle.
- **Helpers** — `helper-js-eval-layer`, `helper-framework-input-fill`, `helper-spa-wait-ladder`, `helper-tab-attach-vs-activate`, `helper-trace-telemetry`, `helper-sharp-edges`, `agent-helper-extension`: js() contract, framework-aware fill, three SPA waits, attach-vs-activate split, runner-side tracing, surprising return shapes, user extensibility.
- **Recorder** — `recorder-folder-marker-whitelist`, `recorder-auto-rollover`, `recorder-redaction-at-write`: cross-process marker state, activity-based rollover, generation-time redaction.
- **Video** — `video-brief-validation`, `video-summary-projection`, `video-cadence-budget-gates`, `video-integrity-gates`, `video-browser-review-harness`, `video-render-preflight-ladder`, `video-click-safe-camera`, `video-mask-raster-plane`, `video-export-choreography`: reject-don't-ignore brief validation, sanitized summary with a sourceLine-keyed reveal ledger, sticky-narration + hard-budget compile gates, hash-pinned review/export gates, sentinel-line browser harness, runtime accumulate-all-errors preflight gating export, click-safe camera framing that never hides the action, pixel-faithful offline mask rasterization for human review, and fail-closed CDP export choreography.
- **Launcher & extensibility** — `dev-launcher-env-namespacing`, `domain-skill-exemplar-extractor`: dev-mode multi-instance namespacing ahead of any Python import, and the env-driven site-script contract taught by one decisive exemplar.
- **Auth & telemetry** — `auth-cli-dual-audience`, `telemetry-detached-optout`: three-path CLI auth with dual-format output; detached, key-name-allowlisted, opt-out telemetry.
- **Cloud ops** — `cloud-zombie-reaper`: REST reaper for leaked billed sessions (liveness-by-absent-field pagination, string-typed costs).

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
browser-harness (MIT), `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926` (v0.1.9); Codebase Memory project `browser-harness` (`/mnt/hdd/utopia/inspo/browser-harness` → canonical `/mnt/hdd/utopia/inspo/agents/browser-harness`, live symlink), full mode, 2,669 nodes / 4,885 edges, head==base==pin re-verified 2026-08-24 pass 4, origin fetch behind=0. All cited source/test paths returned `no_recorded_issue` + `metadata_match` via check_index_coverage. Legacy 4-ref leaf fully swept to capsule-v2 (2026-08-23 frontier-agents lane pass 1). Pass 4 (2026-08-24 deepening-B lane): fresh-eye census found the root launcher + mask/export video_render internals + the claude.ai extractor exemplar uncited → +4 capsules at unchanged pin.

## Full view (memory graph)
Revalidate `browser-harness` before porting: run `index_status --project browser-harness --verbose`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record root, branch, commit, mode, node/edge counts, freshness, and coverage caveats; source and direct tests decide shipped claims. Direct-test density is highest on admin lifecycle (test_admin.py), IPC payloads (test_ipc.py), session/set_session semantics (test_daemon.py), waits/fill/js (test_helpers.py, integration/test_js.py); recorder/telemetry/auth/video modules carry in-capsule deterministic-anchor caveats where no suite exists.

## Boundaries
Adopt the daemon lifecycle, helper API, recorder, video-composition contracts, and the IPC/auth/telemetry plumbing; adapt CDP transport details, video encoders, Browser Use cloud specifics, and BH_*/BU_* env names; omit domain-skills content (~100 site-specific markdown files), the interaction-skills docs corpus, and claude-plugin packaging unless porting the whole product shape. The two Python domain-skills utilities are mined as pattern exemplars (`domain-skill-exemplar-extractor`, `cloud-zombie-reaper`), not product surface. Coverage caveats are recorded in-capsule where a seam has no direct upstream unit test (Windows token path, live-Chrome discovery ladder, patient handshake, tracer, recorder/telemetry/auth/video internals, root bash launcher).
