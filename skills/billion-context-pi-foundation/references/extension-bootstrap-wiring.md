<!-- capsule-v2 -->
# Extension bootstrap wiring — which host events must an extension hook at startup, and why is host auto-compaction cancelled rather than configured?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** What is the minimal correct wiring order for a context-owning extension (compaction cancel, lifecycle, per-call transform, tools, commands), and what must re-run per LLM call instead of at session start?

## createAcpExtension: cancel compaction → wire lifecycle → wire transform → register surfaces
**Path/Symbol:** `src/index.ts`: `createAcpExtension` (:41), `wireCompactionDisable` (:65-67, comment :68-69), `wireSessionLifecycle` (:73-126), `collectOriginals` custom_message mirror (:499-515); tool/command registration :56-64.
**Signature:** `(pi: ExtensionAPI) => void`; hooks: `session_before_compact`, `session_start`, `session_shutdown`, `context` (per LLM call), `before_agent_start`.
**Data Shape:** delegate tools are registered INSIDE the session_start callback (deferred, gated on config) while the four context tools + commands register synchronously in the factory.

### Decisive source
```ts
// src/index.ts:52-56 — ACP owns compression; cancel Pi's built-in auto-compaction
// entirely (mirrors opencode-acp requiring opencode's compaction.auto = false).
function wireCompactionDisable(pi: ExtensionAPI): void {
  pi.on("session_before_compact", () => ({ cancel: true }));
}
```

**Flow:** factory wires compaction-cancel FIRST (a second compressor on one context = two writers corrupting each other) → session_start: invalidate cached state store, clear nudge tracking (the Set would grow unbounded across a long-lived process), load+apply user config with debug propagation, conditionally register delegate/wait/cancel tools (`delegate !== false`), fire-and-forget update check + settings self-patch, bind widget with `runningRunsSnapshot` → session_shutdown: widget dispose + log close → `context` event runs the transform spine every LLM call. Two per-call details a porter will get wrong: (1) `collectOriginals` mirrors Pi's convertToLlm by projecting `custom_message` entries as role:"user" — using a literal "custom" role gets the message DROPPED on rebuild (:237-244); (2) the update check fires in BOTH session_start and the context handler because "resuming a long-running session never re-fires session_start" — safe only because checkForUpdate throttles internally.
**Invariant:** (1) exactly ONE compression writer per context — host auto-compaction must be cancelled, never tuned; (2) per-process caches (nudge Set, state store) reset on every session_start or they leak across sessions; (3) anything needed for resumed sessions (update check) belongs on the per-LLM-call path behind its own throttle, not only on startup.
**Probe:** `tests/integration.test.ts:72` ("context handler tags every message… even when length matches event.messages" — proves the wired handler returns transformed arrays); `tests/compat.test.ts:14` (formatSystemPromptForEvent preserves base prompt — the before_agent_start wiring contract).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "wireCompactionDisable session_start registerTool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wiring ORDER and the compaction-cancellation stance for any extension that owns context management. Adapt event names to your host's lifecycle surface. Omit deferred delegate-tool registration if your platform allows late registration unconditionally.
