# Work record: framer-motion scroll plane (learn --auto pass 1)

## Verified pass
Restored the missing Codebase Memory index for the pinned framer-motion source, verified it ready, and closed the deferred scroll-plane seam in `references/use-scroll-surface.md` from pinned source.

## Source and evidence
- Repository: framer-motion / Motion monorepo, MIT, `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36` (tag v13.1.1), checkout `$REFERENCE_ROOT/ui-framer-motion`.
- Index: Codebase Memory `ext-ui-framer-motion`. Full mode, **10,737 nodes / 27,091 edges**, skipped 0, parse_partial ×6 (dev fixture HTML + `framer-motion/src/index.ts:4` and `debug.ts:1` barrel lines; none cited). Status ready; node/edge counts match the capsule. No dependencies installed.
- Scroll plane: `packages/framer-motion/src/render/dom/scroll/*`: offset resolution, event fan-out (ONE scroll+resize listener per container, frameloop read→preUpdate), progress computed from `scrollLength` and offsets; native ScrollTimeline fast path when supported.
- Direct tests: `render/dom/scroll/__tests__/index.test.ts` (present upstream; not executed (no workspace deps in clone; caveat recorded, not fabricated green).

## Decision and counter-evidence
- Bound: checkout HEAD == recorded capsule pin (`1b037b0032578b52af94b06ff3920bfa0aaa5e36` verified via `git rev-parse HEAD` before indexing).
- Corrected previous capsule guidance: the deferred pass targeted `value/scroll/*`, which does not exist at v13.1.1 (the plane lives at `render/dom/scroll/*`).
- Counter-evidence: `progress()` returns 1 on zero-length range; offset interpolation builds `interpolate(offsets, …, { clamp: false })` and then wraps the result in `clamp(0, 1, …)`, so the target/offset lane is hard-clamped to [0,1] (the plain `scrollTop` lane is not). Graph probes must be re-checked if the engine's file layout changes again.

## Omitted or unresolved
- Native ScrollTimeline (`supportsScrollTimeline` / `observeTimeline`) internals: CLOSED in pass 2 where `attachToAnimation` routes to natively supported timelines and the timeline is mappable; `observeTimeline` polls `frame.preUpdate`, callback invoked only on `prevProgress` change; JS fallback via `scrollTimelineFallback` (`currentTime.value = progress*100`). Unmappable target+offset falls back to JS, never guessed.
- `attach-function.ts` / `attach-animation.ts` wiring: READ (pass 2); `scroll()` picks `attachToFunction` for 2-arg callbacks/target-offset tracking, `attachToAnimation` for playback objects.
- Other framer-motion leaves (springs, follow-value, frameloop) already have capsules; the index restore makes them freshly checkable.

Framer-motion group is **COMPLETE for its scoped seams** (public shape + value contract + scroll plane + native path).

## Next target
- **Group terminal: COMPLETE (pass 2 closed).** Chained \`/learn --auto\` loop continues: recompute eligibility from `list_projects` + pack provenance. Queued seams with named questions: `AgentTeamsRuntime` scheduling internals (busy-suppression / retry-backoff / mailbox-prepend), channels-telegram (6.4kL long-poll plane), duckdb relation_manager/query_graph extraction + statistics_propagator + storage checkpoint serialization, jetbrains-phpstorm-light JS-helper-process planes, goose transport plane. Blocker: dub + grist-core (pinned checkouts drifted past recorded pins) -> route to /inspo.

**Queue dispositions verified 2026-09-02 (do not re-probe without a new porting question):** TheAgenticBrowser (`<legacy-theagenticbrowser-index>` ready 529n/1699e, pin HEAD==71daa28): queued "AgentTeamsRuntime/scheduling" seams DO NOT EXIST in this repo; leaf is saturated for in-scope claims (misqueue). goose (ready 118185n/316888e, pin 2eb3ab1001): transport plane covered by 37 refs; leaf Boundaries declare ACP/session hooks out-of-scope; SATURATED. turso (ready 50306n/353465e, pin 1654d1587): drift-gated; re-entry only on a new upstream wave past the 2026-08-24 gates. duckdb lacks a live index entry; phpstorm-light index ready (45k nodes) but jetbrains-internals-foundation already carries pass-19 recovery; only a NEW product plane or a named porting question triggers work -> /inspo / /learn with the question. copilotkit (pin e9387e04): STILL blocked on index restore approval (/inspo gate; do not auto-index); next real target when approved: channels-telegram long-poll plane mine. bruno (checkout `$REFERENCE_ROOT/external/bruno` HEAD 675965612f): same missing-index class (`ext-bruno` not in census); queued pass-2 seams: bruno-lang tooling + gRPC client internals; joins the index-restore batch gate. Full-leaf marker sweep 2026-09-02 found NO other real unmined seams (all remaining "deferred/queued" hits were prose in covered capsules).

**Index restores APPROVED + mined (2026-09-02, --loop run):** copilotkit (e9387e0483…) → `ext-copilotkit` ready (157,698n/582,076e); TELEGRAM seam COMPLETE (`telegram-long-poll-loop-guard.md` + loader + map). bruno (675965612f) → `ext-bruno` ready (27,553n/96,755e); gRPC TRANSPORT seam COMPLETE (`grpc-client-transport.md` + loader + map; extending-backlog target closed). Remaining bruno candidates: node-vm CJS loader, bru shims (580L), error-formatter (752L), assert-runtime (585L), bruno-lang transpiler units, bruno-converters. Remaining copilotkit: channels-discord components-v2/modal, teams download/graph-files, whatsapp render/message, core memory/threads/intelligence/micro-redux, runtime v2 channel-manager.
