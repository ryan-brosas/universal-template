<!-- capsule-v2 -->
# Codex bridge CLI-relay shim — how do you make a model call host tools through a bash tool when the runtime's MCP registration is broken upstream?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When a sandboxed runtime cannot register MCP tools as model-callable (upstream bug), how does the in-sandbox bridge turn the agent's own bash tool into a safe, correlatable host-tool transport?

## Zero-credential shim script + fail-closed command recognition
**Path/Symbol:** `packages/harness-codex/src/bridge/cli-relay.ts` — `CLI_SHIM_FILENAME` (:29), `buildCliShimScript` (:31–68), `parseToolRelayCommands` (:91–99) over `parseToolRelayCommandsInternal` (:101–139), `parseDirectToolRelayArgv` (:141–157), `extractShellEvalCommand` (:159–167), `splitShellAndCommands` (:169–210), `parseShellWords` (:212–268); wiring in `packages/harness-codex/src/bridge/index.ts` — shim write (:105–121), event-loop interception (:235–253).
**Signature:** `buildCliShimScript({relayPort: number}): string`; `parseToolRelayCommands({command: string, cliShimPath: string}): Array<{toolName: string; input: unknown}> | undefined`.
**Data Shape:** shim = self-contained Node ESM text embedding ONLY the relay port (no auth material); recognition output = one `{toolName, input}` per recognized segment, or `undefined` for anything not provably a pure relay invocation.

### Decisive source
```ts
// cli-relay.ts:141–157 — recognition is EXACT argv match, 3–4 words only
if (argv.length < 3 || argv.length > 4) return undefined;
if (argv[0] !== 'node' || argv[1] !== cliShimPath) return undefined;
const toolName = argv[2];
if (!toolName) return undefined;
try {
  return { toolName, input: JSON.parse(argv[3] ?? '{}') };
} catch {
  return undefined;
}
// cli-relay.ts:101–139 — compound commands: EVERY &&-segment must be a relay
// command or the whole thing is unrecognized (fail-closed)
const commands = splitShellAndCommands(command);
if (!commands) return undefined;
if (commands.length > 1) {
  const relayCalls: Array<{ toolName: string; input: unknown }> = [];
  for (const nestedCommand of commands) {
    const nestedCalls = parseToolRelayCommandsInternal({ command: nestedCommand, cliShimPath, depth });
    if (!nestedCalls) return undefined;
    relayCalls.push(...nestedCalls);
  }
  return relayCalls;
}
// index.ts:235–253 — item.started pre-authorizes BEFORE the HTTP request can
// arrive; relay commands never reach the consumer stream
if (cliShimPath && event.item?.type === 'command_execution') {
  const relayCalls = typeof event.item.command === 'string'
      ? parseToolRelayCommands({ command: event.item.command, cliShimPath })
      : undefined;
  if (event.type === 'item.started' && relay && relayCalls) {
    for (const relayCall of relayCalls) { relay.authorizeToolCall(relayCall); }
  }
  if (relayCalls) {
    stepTracker.observeEvent({ event, itemId: event.item.id });
    continue;
  }
}
```

**Flow:** runTurn starts the loopback relay and writes the shim into `--cli-shim-dir` when the start frame carries tools → the host adapter framed the invocation contract into the first user message (see harness-codex-cli-shim-host-tools.md) → Codex executes `node <shim> <tool> '<json>'` via its bash tool → the bridge sees `item.started`, parses every `&&`-segment, and mints an exact-match authorization per call → the shim POSTs to the relay, which consumes the authorization, emits `tool-call` to the host, awaits `requestToolResult`, emits `tool-result`, and answers the shim → the bridge suppresses ALL relay-command events from the consumer stream (they are observed by the step tracker only) so consumers see clean tool-call/tool-result pairs.
**Invariant:** the shim embeds NO credential (it lives in the model-readable session dir — test asserts absence of 'Authorization'/'Bearer'/'TOOL_RELAY_TOKEN'); recognition is fail-closed — any compound command containing a non-relay segment, any unparseable word (`[;&|<>()\`$]` characters), or any depth beyond two shell-eval unwraps returns undefined and the command falls through to normal bash-tool visibility instead of the relay; authorization is minted on `item.started`, strictly before the shim's HTTP request can exist.
**Probe:** `packages/harness-codex/src/bridge/cli-relay.test.ts` (87L, 6 cases): no-auth-material assertion on the generated script; direct + `/bin/bash -lc "…"` wrapped + multi-`&&` extraction; `node shim … && cat /etc/passwd` ⇒ undefined; `echo <shim>; curl …` (path merely mentioned) ⇒ undefined.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "buildCliShimScript parseToolRelayCommands CLI_SHIM_FILENAME isToolRelayCommand", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the zero-credential shim + exact-match pre-authorization pattern whenever the helper file must live where the model can read it; adopt the fail-closed shell parser shape (exact argv match, all-segments-must-match, character-class rejection, bounded eval unwrap) for any "is this command OURS?" gate; adapt the shim filename/port plumbing and the item.started interception point to your runtime's event vocabulary; omit the workaround entirely once the runtime registers MCP tools natively (the source marks all three hookpoints removable). Caveat: the event-loop suppression itself is pinned only indirectly — cli-relay.test.ts covers the parser, index.test.ts covers config, and no test drives a full relay-command event through runTurn (deterministic read of :236–252).
