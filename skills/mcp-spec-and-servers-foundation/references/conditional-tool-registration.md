<!-- capsule-v2 -->
# Conditional tool registration — how does the reference server gate tools on client capabilities without dead registrations?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821`; Codebase Memory `servers`. **Question:** When must capability-dependent tools be registered, and what does the two-phase registration split look like in a real server?

## Standard tools at construction; client-gated tools after `oninitialized`
**Path/Symbol:** `src/everything/tools/index.ts:26–55` (`registerTools` = 12 standard; `registerConditionalTools` = 7 capability-gated), `src/everything/server/index.ts:81–104` (call sites + `oninitialized` hook + 350 ms roots sync delay), `src/everything/tools/get-roots-list.ts:39–41` (the runtime presence check).
**Signature:** `registerTools(server: McpServer): void` — unconditional; `registerConditionalTools(server: McpServer): void` — requires `server.server.getClientCapabilities()` to be populated (post-initialize); guard pattern: `const caps = server.server.getClientCapabilities() || {}; const supported = caps.roots !== undefined;`.
**Data Shape:** capabilities read back mirror `ClientCapabilities`; task-based conditional tools register via the separate `experimental.tasks.registerToolTask` channel and are therefore NOT counted in `registerTool` call counts.

### Decisive source
```ts
// server/index.ts:94-103 — WHY registration waits, verbatim comments:
server.server.oninitialized = async () => {
  // Register conditional tools now that client capabilities are known.
  // This finishes before the `notifications/initialized` handler finishes.
  registerConditionalTools(server);
  // Sync roots if the client supports them.
  // This is delayed until after the `notifications/initialized` handler
  // finishes, otherwise, the request gets lost.
  const sessionId = server.server.transport?.sessionId;
  initializeTimeout = setTimeout(() => syncRoots(server, sessionId), 350);
};
// get-roots-list.ts:39-41 — presence-gating, not truthiness:
const clientCapabilities = server.server.getClientCapabilities() || {};
const clientSupportsRoots: boolean = clientCapabilities.roots !== undefined;
```

**Flow:** factory constructs `McpServer` with SERVER capabilities → registers 12 standard tools/resources/prompts immediately → on `oninitialized`, CLIENT capabilities are finally readable → registers the 7 conditional tools only when their capability is present (roots / elicitation form+url / sampling / tasks) → roots sync deferred 350 ms so it cannot be swallowed by the still-running initialized handler → cleanup closure stops simulated loops, cleans task-store timers, clears the timeout.
**Invariant:** a tool whose behavior needs a client capability MUST be registered only after initialization or clients see dead tools; the guard is PRESENCE (`!== undefined`) against a `{}`-defaulted object, never truthiness of an empty-object sub-capability. Registration order matters: conditional work must complete inside `oninitialized` before returning, while follow-up REQUESTS (roots/list) must wait for the handler to finish.
**Probe:** direct tests: `__tests__/registrations.test.ts:50–90` pins both branches (all-capabilities mock ⇒ exactly 4 registerTool calls containing `get-roots-list`/`trigger-elicitation-request`/`trigger-url-elicitation`/`trigger-sampling-request` plus `registerToolTask` called; missing-capabilities ⇒ none) and `:30–48` pins the 12 standard registrations; `__tests__/server.test.ts:26` pins that `oninitialized` handler is set.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "registerConditionalTools getClientCapabilities oninitialized registerTool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase split (static catalog at construction, capability-gated additions in `oninitialized`), presence-based gating with `|| {}` defaulting, and post-handler deferral for outbound requests like roots sync; adapt the 350 ms heuristic to your transport's handler semantics; omit unconditional registration of capability-dependent tools — it produces servers that list tools they cannot serve.
