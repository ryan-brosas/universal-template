# local-pi-crew

> **Automatic result processing is implemented; fresh-session runtime verification is still blocked** (see Verification below).

## Automatic operation

- User `input` schedules scout + supervisor; `agent_settled` schedules verifier + advisor; `session_compact` schedules reflector + foundation. Extension-injected input is ignored.
- Hooks return without awaiting model inference. The component uses native `agents.ask` in background jobs, with one pending request per actor and a 10-minute non-checkpoint cooldown, including failures. Compaction deduplication uses exact session/checkpoint/role keys in a bounded 256-key session window. This is not crash-proof exactly-once processing.
- Replies must match the actor and request ID. Useful findings enter Main via `nextTurn`, without triggering a turn. `/crew` shows per-role running, delivered, degraded, retention-queued or retention-accepted results.
- Optional proposals require an exact excerpt from a bounded source file inside the current project; escaping paths and symlinks are rejected. They are retained as **UNVERIFIED PROPOSAL**, tagged `source-checked-proposal`, never silently promoted to facts. Deterministic document IDs deduplicate the same request; separate sessions retain separate provenance.
- Hindsight queue receipts remain `retention-queued`. Neither a receipt nor an accepted API response proves extraction/indexing has completed. Memory failures leave findings deliverable and report degraded status.
- Existing actors/history are reused from the full registry under the creation lock. Replies arriving after shutdown or component replacement are discarded. Work still running in Fabric is subject to its native timeout; there is no custom polling daemon.
- Load this revision in a new Pi session (or a normal supported reload); this session's old component closure is not hot-patched by editing source.

## Project-isolated memory (broker boundary)

Calls made through the session-side broker (`memory.mjs`) are pinned to the canonical Git-root-derived bank `pi-crew-<sha256-24 of common dir>` with `crew-role:<role>` tags. Unresolvable identity and rejected, error-envelope, or malformed Hindsight responses degrade closed. This wrapper is not an actor sandbox: actors have extensions enabled and can bypass it with direct tool calls. `results.mjs` consumes correlated automatic replies and invokes the broker for source-checked proposals. Project identity (`identity.mjs`) is the hash of the canonical common Git directory, so linked worktrees share one project and unrelated clones never mix. Hindsight project config for THIS repository was switched to `isolated-bank` + `projectBankId: pi-crew-8af27f51c186f1f79bc23c49` + `memoryProfile: project-only` + `enableGlobalBank: false` (`.pi/hindsight.json`). Previous values for revert: `scopeMode domain-tagged, projectBankId pi-coding, includeSharedObservations false, enableGlobalBank true, memoryProfile project+global`. Prior shared-bank memories remain stored in `pi-coding`; nothing was migrated or deleted.

A globally loaded pi package whose Fabric component attaches a durable six-actor crew to every trusted project, using only native Fabric mesh (no daemon, no SDK runtime at use time).

## Actors

| Name | Trigger | Delivery | Tools |
|---|---|---|---|
| project-supervisor | agent_settled, tool_error | steer, triggerTurn: true | read, grep, find, ls |
| project-advisor | agent_settled, tool_error | steer, triggerTurn: false | read, grep, find, ls |
| foundation-actor | foundation.requested topic | followUp | read, grep, find, ls, write, edit, bash |
| project-scout | explicit agents.ask | mailbox | read, grep, find, ls |
| project-verifier | explicit agents.ask | mailbox | read, grep, find, ls, bash |
| session-reflector | session_compact via component handler | mailbox | read, grep, find, ls |

## Behavior

- **Attach-once discipline:** component `project-crew` activates on Fabric startup in trusted projects. It skips Fabric children (`PI_FABRIC_*` markers), untrusted projects, and non-root participants. `attach()` preflights every name before creating anything: duplicate existing names and non-idle (running or stopped) actors abort with nothing replaced; idle actors are reused unchanged (model binding and history preserved).
- **Concurrency:** creation is serialized by an mkdir lock at `<project>/.pi/fabric/crew-install.lock` (10s bounded wait; never steals — a crashed installer leaves the lock visible for manual recovery).
- **Reflection:** the component's `session_compact` handler queues exactly-once reflection with the exact triggering session id and compaction checkpoint id (`agents.tell` to session-reflector, deduped per session/checkpoint). It defers to a legacy reflector that natively subscribes `session_compact` **in the same root lineage** (no double trigger); a foreign-rooted native subscriber cannot hear this session's relay, so the component queues the explicit checkpoint instead.
- **Session model pinning:** `/crew-model <provider/id>` pins the model for all six actors in the current session via session-scope bindings (verified working from a non-owner disposable session; owner-gated `scope:"project"` pins stay Fabric-resident). `/crew-model clear` removes the session pin so actors inherit the project default again. The command requires this session's component activation (active.call); it reports per-actor results and never touches project defaults or actor identity.
- **Observer coverage (degraded mode):** Fabric routes host events (`agent_settled`, `tool_error`) only through the owning root; there is no supported actor-root rebinding. If reused crew observers are owned by a foreign root, the component reports state **degraded** (in `/crew`, the session guide, and a startup warning) naming each gap, preserves the actors unchanged, and keeps mailbox routing (scout/verifier/foundation) working. Verified live: second session in a project saw both observers foreign and a real tool_error delivered nothing to the supervisor. Remedy when degraded: remove and recreate the crew (history is lost) or operate mailbox-only.
- **Roles:** `roles/*.md` are project-agnostic and read from disk at each activation; the wrapper instruction pins the project root, shared capability root, and discovery-first capability rules (Fovea, Codebase Memory, context7, Hindsight are discovered and degrade explicitly; never assumed).
- **Isolation:** mesh stays project-scoped (`mesh.actorScope: project`); Hindsight uses each project's existing scope; nothing client-confidential is retained by reflection.

## Install

Already wired: `~/.pi/agent/settings.json` packages contains this directory; `~/.pi/agent/fabric.json` has `mesh.enabled: true` and `components: [{id: "project-crew", component: "local-pi-crew"}]`.

## Verification

`npm test` runs all four suites, including `workflow.test.mjs`: registered input/settled/compact events through native-call test doubles, Main delivery, source checking, broker retention, duplicate/concurrency guards, shutdown, failure envelopes and two-activation registry reuse. A real scout `agents.ask` reply also matched the host response envelope; its validated proposal received a real Hindsight outbox receipt. This proves acceptance into the local queue, not downstream indexing. A fresh-session SDK probe is blocked at import by the installed missing `@earendil-works/pi-server` dependency; normal startup with this revision remains unverified. In this project (`<project-checkout>`) the legacy crew reports degraded with one gap (session-reflector rooted at an older session) while supervisor/advisor remain covered. Live two-project probe (2026-09-05): project A created 6 durable actors, second session reused identical IDs, project B created 6 distinct IDs.

## Session-scope model bindings (tested 2026-09-05)

Fresh-session SDK probe (in-memory SessionManager in this project): component `project-crew` **active** (revision 1, guidance registered), zero extension errors, and all six actors reused unchanged. In a brand-new session every actor resolves to that session's own model until you call `agents.setModel({id, model, scope:"session"})` **in that session**; the old DeepSeek session bindings belonged to the older sessions and do not carry over. Owner-gated `scope:"project"` pins cannot be changed from a fresh session (`agents.setModel` throws owned-by-another-host from any non-owner session). A future `scope:"project"` pin would be inherited only while the session default stays Astra — the component passes the session model at attach time only for *new* actors; reused actors keep their Astra project default. To make new-actor creation use DeepSeek, the creating session must run DeepSeek (or pass `config.model` in the fabric.json components entry). Remedy for any session: `/crew-model zro/deepseek-v4-flash-0731` pins all six for that session (verified: disposable session 01a07048 pinned project-scout successfully; binding and resolved model confirmed deepseek). Note: a session that started before this package was installed cannot resolve the component definition mid-session (`components.reload` fails with 'Fabric component definition is unavailable: local-pi-crew') — only sessions started after installation get `/crew` and `/crew-model`; actor mailbox routing works everywhere regardless. The probes were read-only apart from the disposable session's own binding layer: no actors created, replaced, or model-mutated.

Trust model note: unlike the legacy `.pi/background-actors` setup (mesh-attested definitions v3), this component treats its own package definitions as the source of truth and does not write mesh attestation; the definitions change only when this package changes.
