---
name: pi-acp-foundation
description: "Use when building an Agent Client Protocol (ACP) adapter that bridges an external ACP client (JetBrains IntelliJ, Zed) to a single-session coding agent (pi): stdio NDJSON ACP server wiring, 1:1 session-to-subprocess mapping, pi RPC transport, turn state machine with agent_settled completion, monotonic tool-call statuses, ordered update emission, slash-command expansion, structured edit diffs, and an authenticated IPC bridge that exposes remote MCP tools as pi extension tools."
disable-model-invocation: true
---
# Pi-ACP-Jetbrain: ACP Adapter for a Single-Session Coding Agent

## Use this for
Build an ACP (Agent Client Protocol) adapter that bridges an external ACP client (JetBrains IntelliJ, Zed) to a single-session coding agent (`pi`). The adapter speaks ACP JSON-RPC 2.0 over stdio, maps each ACP session to one dedicated `pi --mode rpc` subprocess, streams pi events as ACP `session/update` notifications, maps pi tool execution to ACP `tool_call`/`tool_call_update` with structured diffs and terminal rendering, expands slash commands, and bridges remote MCP servers (IntelliJ's private IDE MCP) into pi as `ide_<server>_<tool>` extension tools over an authenticated local IPC channel. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. The repo ships a real test runner (`node --import tsx --test test/**/*.test.ts` — 139 tests pass at HEAD), so every capsule's Probe is pinned to a direct on-disk test.

## Load the matching source dump
- `references/acp-stdio-server.md` — the ACP stdio server wiring: NDJSON framing, stream wrappers, terminal-login entrypoint, and teardown.
- `references/session-to-subprocess.md` — the 1:1 ACP-session↔pi-subprocess mapping, single-live-subprocess policy, and session restore.
- `references/pi-rpc-transport.md` — the newline-delelimited JSON RPC transport over pi stdio: request/response correlation, prelude capture, ANSI stripping, and lifecycle.
- `references/turn-state-machine.md` — the turn completion state machine driven by `agent_settled`, queued turns, and cancel semantics.
- `references/monotonic-tool-statuses.md` — the never-downgrade tool-call status tracking and ordered `session/update` emission chain.
- `references/structured-edit-diff.md` — pre-mutation file snapshots + unique-line inference → ACP structured `diff` content.
- `references/bash-terminal-rendering.md` — mapping pi bash tool events to ACP `execute` terminal rendering (delta output, exit meta).
- `references/slash-command-expansion.md` — file-based slash-command loading, arg parsing, substitution, and expansion.
- `references/auth-required-detection.md` — best-effort missing-credential detection → ACP `authRequired` with terminal-auth methods.
- `references/session-discovery.md` — reading pi's own JSONL session files for list/load (title/updatedAt ladders, tail scanning).
- `references/mcp-bridge-ipc.md` — the authenticated per-session IPC server + catalog handshake/registration validation.
- `references/mcp-bridge-transports.md` — the stdio/SSE/ACP MCP transports, IntelliJ SSE-preference ladder, and bounded discovery.
- `references/mcp-result-to-pi.md` — converting MCP results to pi text/image content, schema→TypeBox conversion, and result sanitization.
- `references/startup-info.md` — the synthesized startup-info prelude (pi version, skills, prompts, extensions, IDE bridge status) and update notice.
- `references/pi-settings-merged-precedence.md` — reading pi settings you don't own: global+project deepMerge, back-compat key ladders, typed defaults.
- `references/session-map-store.md` — the corrupt-tolerant versioned `session-map.json` store (~/.pi/pi-acp/) with load-modify-write semantics.
- `references/win-cmd-shell-spawn.md` — portable `pi` spawn: `.cmd`/`.bat` suffix-gated `shell:true`, POSIX never shelled.
- `references/config-options-selectors.md` — model/thinking ACP config options built from pi state with null-model degradation and first-slash model-id parsing.
- `references/extension-ui-hitl-ladder.md` — pi extension UI requests laddered onto ACP request_permission (select→indexed choices, confirm→boolean, rest→cancel-with-marker).
- `references/command-catalog-gates.md` — available-commands filtering: default-hidden extensions, prefix-keyed skill gate, describe fallback.
- `references/prompt-blocks-to-pi.md` — ACP prompt blocks → pi message with marker-preserving downconvert (no silent context loss).
- `references/tool-result-to-text.md` — flattening heterogeneous pi tool results: diff-first → content blocks → bash details ladder → JSON.
- `references/history-replay-normalizers.md` — role-shaped text extraction for history replay; the deliberate user/assistant string-path asymmetry.
- `references/spawn-race-stderr-tail.md` — spawn-ack race → typed `PiRpcSpawnError` taxonomy, ANSI-stripped prelude capture, observed-not-consumed bounded stderr tail, once-only exit fan-out.
- `references/session-store-concurrency.md` — mkdir-lock + mtime-stale reaping + Atomics.wait sync sleep + pid/uuid tmp-rename atomic writes over the session map (8-process concurrency test).
- `references/crash-shutdown-contract.md` — nonzero-exit crash path with bounded best-effort child disposal, handler retention, awaited disposeAll on graceful shutdown.
- `references/turn-settling-hardening.md` — process-exit/dispose settle pending turns, bridge-cancel-before-abort ordering, timeout-raced usage collection, error-via-_meta.
- `references/session-lifecycle-quartet.md` — unstable fork/resume/close/listProviders: spawn-branch-rebind forking that never mutates the source file, three-way cleanup matrix.
- `references/storage-redirect-usage-providers.md` — `PI_ACP_SESSION_MAP` storage redirect, null-means-omit usage projection, sentinel-protocol provider listing.
- `references/startup-inventory-bounds.md` — double-capped skill/prompt/extension enumeration with realpath symlink-cycle protection, injected-or-derived build identity, portable path rendering.
- `references/elicitation-input-slash-args.md` — extension input UI upgraded to ACP form elicitation with timeout fallback; single-pass three-form `$N/$@/${@:s(:l)}` substitution grammar; hint enrichment without reordering.
- `references/list-changed-surfacing.md` — once-per-session staleness notice via diagnostics-delta detection when a bridged server announces tools/list_changed against the immutable snapshot catalog.
- `references/descriptor-redaction-guidance.md` — allowlist-only env passthrough in debug logs; append-only state-aware IDE guidance composition with trailing diagnostics.
- `references/bridge-denylist-jsonrpc.md` — prefix+explicit default denylist for dangerous IDE tools with reviewed env opt-in; shared JSON-RPC settlement kernel across stdio/SSE transports; SSE close/error convergence.
- `references/result-path-confinement.md` — result-side out-of-root path scanning under node/depth budgets where exhaustion fails closed, ancestor-realpath symlink checks.
- `references/mutation-confinement-provenance.md` — throw-don't-rewrite path confinement with existing-ancestor realpath walk, two-dialect patch-target parser, pre/post-open mutation choreography, before-snapshot mutation-provenance audit.
- `references/ide-mode-state-machine.md` — PI_ACP_IDE_MODE off/prefer/required FSM over async catalog arrival: capability indexing, fail-closed mode parse, runtime-not-ready deferral, singleton bridge claim.
- `references/post-turn-inspection-gate.md` — adapter-side direct IDE lint invocation with unwrap→envelope→single-file normalization ladder, budgeted KTS pass, never-throws degrade-to-skipped contract.
- `references/acp-initialize-handshake.md` — initialize/authenticate handshake: protocol-version echo-or-degrade, capability surface incl. unstable sessionCapabilities, Zed terminal-auth `_meta` probe.
- `references/new-session-auth-ladder.md` — newSession post-spawn probe ladder: ok/error envelopes, empty-models=unauthenticated authRequired, three-surface orphan cleanup.
- `references/commands-advertisement-ordering.md` — available_commands_update strictly after the session/new response; first-wins merge of agent commands + file inputs + builtins; legacy fallback.
- `references/adapter-builtin-slash-commands.md` — adapter-side interception of eight built-in slash commands (no model call), terminate-with-end_turn contract, precondition guards before id-less-error RPCs.
- `references/session-load-history-replay.md` — session/load replay driver: role-dispatched chunks + synthetic completed/failed tool-call pairs with bash terminal projection.
- `references/acp-smoke-harness.md` — the scripts/ smoke rig: isolated agent-dir overlay, id-correlated NDJSON harness, semantic error assertions, SIGTERM→SIGKILL close ladder.

## Capsule map
- **ACP server** — `references/acp-stdio-server.md`: `ndJsonStream(input, output)` over stdio, destroyed-stdout-tolerant write, `--terminal-login` re-launch, stdin-end/SIGINT/SIGTERM teardown.
- **Session mapping** — `references/session-to-subprocess.md`: `SessionManager` + `PiAcpAgent.restoreSession`, one live pi subprocess per connection (`closeAllExcept`), in-flight restore dedup, session-file cleanup on failure.
- **Pi RPC transport** — `references/pi-rpc-transport.md`: `PiRpcProcess` — NDJSON request/response over pi stdio, `crypto.randomUUID()` correlation ids, prelude capture, ANSI stripping, spawn-error taxonomy, SIGTERM→SIGKILL teardown.
- **Turn state machine** — `references/turn-state-machine.md`: `PiAcpSession.prompt` — pending turn + queue, completion ONLY on `agent_settled` (not `turn_end`/`agent_end`), `cancelRequested` → `cancelled` stopReason.
- **Tool statuses** — `references/monotonic-tool-statuses.md`: `currentToolCalls` map never downgrades `pending`→`in_progress`→`completed`; `lastEmit` promise chain serializes `session/update` delivery.
- **Edit diffs** — `references/structured-edit-diff.md`: `fileSnapshots` captured at `tool_execution_start`, `findUniqueLineNumber` (must be unique), `oldText`/`newText` diff on completion.
- **Bash terminal** — `references/bash-terminal-rendering.md`: `bashTerminalContent`/`bashTerminalInfoMeta`/`bashTerminalOutputMeta`/`bashTerminalExitMeta`, `bashOutputDelta` (prefix-diff), `bashExitCode`.
- **Slash commands** — `references/slash-command-expansion.md`: `loadSlashCommands` (user→project), `parseCommandArgs` (bash quotes), `substituteArgs` ($1/$@), `expandSlashCommand` in `session.prompt`.
- **Auth** — `references/auth-required-detection.md`: `maybeAuthRequiredError` substring ladder → `RequestError.authRequired`; `getAuthMethods` dual terminal-auth shape.
- **Session discovery** — `references/session-discovery.md`: `listPiSessions` — JSONL walk, first-line header, tail title/updatedAt ladders, `findPiSession`.
- **MCP bridge IPC** — `references/mcp-bridge-ipc.md`: `McpIpcServer` — token-authenticated single-client socket, catalog set before spawn, `validateCatalogRegistration` (schema-hash + completeness), hello_ack handshake.
- **MCP transports** — `references/mcp-bridge-transports.md`: `AcpMcpBridge` — stdio/SSE/ACP transports, IntelliJ SSE-preference ladder (`IJ_MCP_SERVER_PORT`), bounded cursor-paginated discovery, immutable per-session catalog.
- **MCP result mapping** — `references/mcp-result-to-pi.md`: `schemaToTypeBox` (JSON Schema→TypeBox with depth/node guards), `mcpResultToPiResult` (text/image/resource, sensitive-key redaction), `prepareToolArguments`.
- **Startup info** — `references/startup-info.md`: `buildStartupInfo`/`buildBridgeStartupInfo` — pi version, skills/prompts/extensions discovery, IDE bridge status, `buildUpdateNotice` semver check.
- **Settings mirror** — `references/pi-settings-merged-precedence.md`: `getMergedSettings`/`deepMerge` — project-over-global object-recursive merge, corrupt-file→`{}`, back-compat ladders (`skills.enableSkillCommands`, `quietStart`) ending in typed defaults.
- **Session map store** — `references/session-map-store.md`: `SessionStore` over `~/.pi/pi-acp/session-map.json` — version-checked corrupt-to-empty loads, whole-file load-modify-write, idempotent delete.
- **Windows spawn** — `references/win-cmd-shell-spawn.md`: `defaultPiCommand`/`shouldUseShellForPiCommand` — `.cmd`/`.bat` suffix gate on the RESOLVED command decides `shell:true`; POSIX always shell-less.
- **Config selectors** — `references/config-options-selectors.md`: `getSessionConfiguration`/`buildConfigOptions`/`setSessionModel` — model-first option order, null-models→omit selector, unknown-current→first-listed, static six-level thinking table with medium fallback, first-slash-only id split.
- **Extension UI HITL** — `references/extension-ui-hitl-ladder.md`: `handleExtensionUiRequest` ladder onto `requestPermission` — select→`choice-N` codec, confirm→boolean, input/editor/notify→cancel-with-visible-marker; single-response termination invariant.
- **Command catalog** — `references/command-catalog-gates.md`: `toAvailableCommandsFromPiGetCommands` — extension source hidden by default, `skill:` prefix gate, dual-envelope tolerance, `(source:location)` describe fallback.
- **Prompt downconvert** — `references/prompt-blocks-to-pi.md`: `promptToPiMessage` — inline text/resources as bracketed markers, images to raw base64, audio → honest size-tagged unsupported marker.
- **Tool-result flatten** — `references/tool-result-to-text.md`: `toolResultToText` precedence diff → text blocks → bash stdout/stderr/exitCode details ladder → guarded JSON.
- **Replay normalizers** — `references/history-replay-normalizers.md`: `normalizePiMessageText` (string fast-path) vs `normalizePiAssistantText` (array-only) — text-block-only replay filters thinking/tool payloads.
- **Spawn race & stderr tail** — `references/spawn-race-stderr-tail.md`: spawn-ack vs error race → `PiRpcSpawnError` ENOENT/EACCES taxonomy, prelude capture, 200-line observed stderr tail, exit fan-out to all pendings.
- **Session-store concurrency** — `references/session-store-concurrency.md`: mkdir-lock + stale reaping + Atomics.wait sleep + tmp-rename atomic save; only mutations lock, reads stay lockless.
- **Crash/shutdown** — `references/crash-shutdown-contract.md`: `exitOnCrash` nonzero-exit contract with 2s disposal budget; retained agent instance; awaited disposeAll; idempotent shutdown latch.
- **Turn settling hardening** — `references/turn-settling-hardening.md`: exit/dispose settle pending turns; bridge-cancel BEFORE slow abort RPC; 2.5s-raced usage; `_meta.piAcp.error`.
- **Lifecycle quartet** — `references/session-lifecycle-quartet.md`: fork (dedicated subprocess on stored file, never mutates source), resume, close-keeps-file, ephemeral provider listing.
- **Storage redirect & usage/providers** — `references/storage-redirect-usage-providers.md`: `PI_ACP_SESSION_MAP`, null-means-omit usage math, `_provider` sentinel protocols.
- **Startup bounds** — `references/startup-inventory-bounds.md`: per-section caps + 64KB markdown cap + realpath visited-set cycles; tsup-injected or git-derived build identity.
- **Elicitation input & slash args** — `references/elicitation-input-slash-args.md`: form elicitation with timeout fallback for extension input; single-pass substitution; hint merge without reorder.
- **List-changed surfacing** — `references/list-changed-surfacing.md`: diagnostics-delta detection + once-latch → one `session_info_update` staleness notice per session.
- **Redaction & guidance** — `references/descriptor-redaction-guidance.md`: allowlist-only descriptor env passthrough; append-only IDE guidance + trailing policy diagnostics.
- **Denylist & JSON-RPC kernel** — `references/bridge-denylist-jsonrpc.md`: `xdebug_*` prefix + explicit denylist with `PI_ACP_IDE_EXTRA_TOOLS` opt-in; shared `settlePendingJsonRpcResponse`; SSE close/error convergence.
- **Result path confinement** — `references/result-path-confinement.md`: result-side out-of-root scan with 5000-node/16-depth budgets failing closed in required mode.
- **Mutation confinement & provenance** — `references/mutation-confinement-provenance.md`: throw-don't-rewrite paths, unified+V4A patch-target parsing, pre/post-open choreography, before-snapshot violations audit.
- **IDE mode state machine** — `references/ide-mode-state-machine.md`: off/prefer/required FSM, capability index → availability evaluation, runtime-not-ready defer cap 500, singleton bridge claim.
- **Post-turn inspection gate** — `references/post-turn-inspection-gate.md`: adapter-side lint via `callRemoteTool`, normalization ladder, budgeted KTS scripts with one-shot retry, versioned JSON+MD reports.
- **ACP handshake** — `references/acp-initialize-handshake.md`: `initialize` echoes requested protocolVersion only when === 1, always returns authMethods (Zed `_meta['terminal-auth']` gated by client probe), capability flags mirror implemented methods; `authenticate` is a success no-op.
- **New-session auth ladder** — `references/new-session-auth-ladder.md`: parallel ok/error probe envelopes; models-auth-error → authRequired, non-auth → internalError, EMPTY model list → unauthenticated; every failure runs cleanupFailedNewSession (close + unlink session file from state-or-store + store.delete).
- **Command advertisement** — `references/commands-advertisement-ordering.md`: `available_commands_update` deferred one macrotask AFTER the response (Zed drops unknown-sessionId notifications); mergeCommands first-wins over [pi commands + file inputs] + builtinAvailableCommands(8); getCommands failure falls back to legacy file list.
- **Builtin slash dispatch** — `references/adapter-builtin-slash-commands.md`: prompt() intercepts /compact /session /name /steering /follow-up /changelog /export /autocompact before pi (`proc.prompts.length===0` pinned), every branch ends `end_turn`, export guards the id-less-parse-error precondition.
- **History replay** — `references/session-load-history-replay.md`: loadSession tears down an active same-id subprocess, replays getMessages role-by-role into user/agent chunks and synthetic completed-or-failed tool_call pairs (bash = full terminal metas; others kind-mapped text), restored bridge info survives quiet mode only when high-signal.
- **Smoke harness** — `references/acp-smoke-harness.md`: scripts/lib/acp-smoke.mjs — F-027 isolated agent-dir overlay (symlink config, temp sessions/cache/fabric), id-correlated NDJSON harness with deadline fan-out, expectError(code,messagePattern) semantic assertions, waitForUpdate predicate poll, SIGTERM→SIGKILL close + assertExited.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Each new capsule must carry Path/Symbol, Signature, Data Shape, a labelled decisive source excerpt, Flow, Invariant, a direct-test Probe, and a `search_graph` Retrieve.

## Provenance
pi-acp-jetbrain (MIT, `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; pass 1-2 pin was `27aac05f53264bf6c449c41f86bf93dc4c54feed` = base_sha, ZERO drift then; pass 3 drift re-entry 2026-08-24 ff-pulled +258 commits to v0.0.40; pass 4 same-pin deep pass 2026-08-26 — ledger row was stale at 0/0/0 and reconciled; work record created at `inspo/pi-acp-work/`); Codebase Memory project `pi-acp` — REINDEXED IN PLACE at the new path `/mnt/hdd/utopia/inspo/pi-ecosystem/pi-acp` (1350 nodes / 4350 edges, full mode; the old registration served the pre-move path `/mnt/hdd/utopia/inspo/pi-acp`, now a symlink — refresh-in-place SUCCEEDED this time, no stuck twin). Two files have `parse_partial` ranges (`src/acp/session.ts` :37 and `src/acp/pi-sessions.ts` :45,:48) — constructs in those ranges may be missing from the graph; source was read directly. `.git/.pi/.veda/dist/node_modules` excluded by design. Pass-3 gate-5 REAL RUNNER: `npx tsx --test` at the pin across 11 suites = 145/145 GREEN (session-store concurrency w/ real worker processes, ide-inspection, default-ide-deny-list, mcp-json-rpc, session-usage, build-info, providers, slash-commands, exit-on-crash, acp-mcp-extension, gate-hardening, startup-info-bounds incl. live symlink-cycle test ~140ms bounded, entrypoint-shutdown with a real child pi). Pass-4 gate-5: direct suites re-executed GREEN at HEAD (auth-methods-terminal-auth-meta 2/2, builtin-commands 2/2, merge-commands 1/1 [mirror-impl caveat], new-session-runtime-startup-errors 2/2, session-load-toolresult 1/1) + REAL smoke run `node scripts/smoke-session.mjs` → `OK smoke-session (dist 3d5ffcd2e2d8)` against the built pin; check_index_coverage no_recorded_issue ×7 cited paths at gen-matched full index.

## Full view (memory graph)
Revalidate `pi-acp` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note the `parse_partial` ranges above and prefer direct source reads for `pi-sessions.ts` and `session.ts` flagged lines.

## Boundaries
Adopt the ACP stdio server wiring, the 1:1 session↔subprocess mapping with single-live-subprocess policy, the pi RPC NDJSON transport (spawn-race error taxonomy + bounded stderr tail), the `agent_settled`-driven turn state machine with exit/dispose settling, monotonic tool-call statuses, the ordered `session/update` emission chain, structured edit diffs, bash terminal rendering, slash-command expansion (now with elicitation-backed input UI), session discovery, the authenticated IPC MCP bridge with catalog registration validation and default IDE-tool denylist, the MCP result→pi mapping with result-side path confinement, bounded startup inventory, crash-safe shutdown semantics, and the locked+atomic session-map store. Adapt the pi executable path/args (`--mode rpc --no-themes`), the session-map storage location (`~/.pi/pi-acp/session-map.json`, redirectable via `PI_ACP_SESSION_MAP`), the IntelliJ-specific SSE descriptor handling and denylist names, and the auth-method launch spec to the host. Omit the Pi extension wiring internals you don't port (the `acpMcpBridgeExtension` activation details beyond the mode FSM), the JetBrains-specific `toolDescription` guidance notes, KTS scripted-inspection plumbing unless your IDE has an equivalent, and the `@agentclientprotocol/sdk`/`typebox` vendor contracts unless a target needs them.
