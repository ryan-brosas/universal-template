<!-- capsule-v2 -->
# Extension entry composition — event-hook choreography, ESC stop-the-world debounce, and the message_end handoff boundary

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** given a host extension API of lifecycle events (`session_start`, `before_agent_start`, `tool_result`, `message_end`, …), how do you wire captured tools, ownership reassertion, advisory steering, and deferred handoffs so every concern fires at the RIGHT hook — exactly once?

## Connected graph-selected seam
**Path/Symbol:** `src/index.ts` whole file (640L): `piFabric(pi)` entry (:99), `registrationFrom` validator (:80-97), skills-dir discovery (:67-78, :167-170), ownership reassertion factory (:144-153), provider-register subscription (:155-165), `applyFabricMode`/`suspendToolCapture` (:207-217), ESC halt (:229-283), ash replay (:288-298), session_start (:300-328), session_tree (:332-336), input/agent_start/agent_end/turn_end (:338-360), agent_settled (:362-384), tool_call/tool_result (:386-391), read-marker expansion (:393-408), usage-merge message_end (:410-421), HANDOFF boundary message_end (:427-473), tool_execution_end (:475-482), session_compact (:484-487), compaction hook (:492-509), context filter (:511-539), before_agent_start guidance+advisory (:541-598), actor observers (:600-603), session_shutdown (:605-619), turn-scoped reassert (:625-627).
**Signature:** `default async function piFabric(pi: ExtensionAPI): Promise<void>`; the handoff handler returns `{message: {...outer, content:[{type:"text",text}], details, isError: !boundarySucceeded}}`.
**Data Shape:** `pendingHandoffs = Map<outerToolCallId, PendingFabricHandoff>` populated by `state.claimHandoff` inside fabric_exec execute() and consumed at the boundary.

### Decisive source
```ts
// A lone Esc that lands while Fabric is already in a stop-the-world
// halt is a no-op: the gate is armed and resumes on the next message,
// so don't repeat the notice — a double-Esc to open /tree would
// otherwise pop it on every press. Only the first Esc of a halt
// session notifies.
if (state.actors.halted) return;
halted = state.actors.haltAll().halted;
// ...
if (halted === 0) return; // lone Esc with no active actors stays silent
```

**Flow:** CONSTRUCT once per extension load: catalogs/advisor/state/ui + `installRegisteredToolCapture` anchored on the fabric_exec tool definition with an INACTIVE initial policy (capture starts off until a session initializes config) + ONE shared `FABRIC_PROVIDER_REGISTER_EVENT` subscription whose unsubscribe is captured for shutdown. PER SESSION: session_start clears pendingHandoffs/approvals, suspends capture, resets advisor then replays ASH from the current branch (hints persisted as custom messages, organic use as tool calls — nothing else stored), initializes state, RE-CREATES the fabric_exec tool object in place (Object.assign so Pi's registry keeps identity), applies mode, starts UI, installs ESC halt (TUI-only, gated on ui.haltOnEscape ∧ mesh.enabled ∧ terminal-input capability). The ESC handler debounces 60ms so split escape SEQUENCES (arrow keys) never trigger: any non-ESC byte cancels the pending timer; a confirmed lone ESC halts all actors but is OBSERVED NOT CONSUMED (Pi's native cancel still runs); repeat ESC during an armed gate no-ops silently; zero halted actors no-ops the notice. before_agent_start rebuilds system-prompt guidance per mode, restores Pi's omitted skill catalog in full-code mode, and evaluates one-shot capability advisories ONLY when capture hides tools. agent_settled awaits in-place prewalk settlement AND `compact.maybeCommit` BEFORE returning — ExtensionRunner publishes its public settled event only after handlers resolve, so compaction always settles inside the boundary. THE BOUNDARY: a second message_end handler matches `role==="toolResult" && toolName==="fabric_exec"` with a claimed pendingHandoff, runs the child via `state.runHandoffAtBoundary`, formats + middle-truncates, appends the rearm directive AFTER truncation so it survives budgeting, flips details.success and isError from actual boundary outcome. Shutdown unsubscribes the shared listener FIRST, then clears maps/halt/UI/capture policy/ownership/lifecycle, `await state.shutdown()` in try / `toolCapture.dispose()` in finally.
**Invariant:** (1) Tool-ownership reassertion is registered TWICE deliberately — schedule-based (catalog refresh) and turn-scoped (`before_agent_start`) — because Pi auto-activates late-registering tools on every refresh; the ready-gate prevents reading uninitialized config. (2) The single shared provider-listener is created ONCE at module level and survives re-initializations; only session_shutdown removes it (test pins listener count 1 across three cycles). (3) Invalid provider registrations THROW inside the event callback — a malformed third-party registration fails loudly instead of poisoning state. (4) Handoff consumption deletes the pending map entry BEFORE awaiting so a re-entrant message_end can never double-run the fork. (5) The rearm directive lands after truncation and gates on "still armed" — one-shot handoffs stay silent. (6) `message_end` usage merge runs in an EARLIER handler than handoff (order matters: classifier usage folds into native usage before persistence).
**Probe:** `tests/extension-shutdown.test.ts:9` ("unsubscribes shared provider listeners across reloads"), `tests/fabric-controller.test.ts:85` ("passes every actor callback to the dashboard so all pickers are available" — hint strings `m model` / `e thinking` / `v events` / `c clear` gate each callback wiring), `:123` ("routes Main dashboard messages through FabricState" — queueUserMessage(sessionId, text, "steer")), `tests/main-agent.test.ts:140` remote-guard pins the local-only delivery this composition relies on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "installHaltOnEscape applyFabricMode registrationFrom pendingHandoffs runHandoffAtBoundary session_shutdown", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hook-to-concern mapping table (which concern lives on which lifecycle event), the debounced observed-not-consumed ESC pattern, and delete-before-await boundary claims; adapt event names to your host. Porters get this wrong by installing stop-the-world without sequence debouncing (arrow keys halt actors), or by running the handoff fork before the outer tool result is finalized.
