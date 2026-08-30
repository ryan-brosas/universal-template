<!-- capsule-v2 -->
# Dual-mode stream dispatch — how do I route turns through two bridge modes (host-tools MCP vs native agent) over one session pool?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When the same pooled agent can run either its native internal tool loop or a host-tools bridge, how do I dispatch turns and handle continuation vs supersession without corrupting the stream?

## Mode split at stream entry; three pi-tools turn outcomes
**Path/Symbol:** `src/providers.ts:streamDroid` (431-446), `streamDroidPiTools` (448-548), `streamDroidAgent` (550-632).
**Signature:** `function streamDroid(model: Model<Api>, context: Context, options: SimpleStreamOptions | undefined, cfg: ResolvedConfig, instanceRuntime: InstanceRuntime): AssistantMessageEventStream`
**Data Shape:** `cfg.mode` ∈ `"agent" | "pi-tools"`; both modes return an `AssistantMessageEventStream` synchronously and drive it from a detached async IIFE. pi-tools keeps per-entry `activeTurn: PiToolsTurnState | null` with `phase`, `consumerAbort: AbortController`, `board`.

### Decisive source
```ts
const runtime = resolveCallRuntime(options, instanceRuntime);
if (cfg.mode === "pi-tools") {
  return streamDroidPiTools(model, context, options, cfg, runtime);
}
return streamDroidAgent(model, context, options, cfg, runtime);
```

pi-tools turn routing (continuation / supersede / new turn):
```ts
// Continuation: Pi executed tools and is delivering results into the hanging MCP handlers.
if (isAwaitingPiTools(entry.activeTurn) && entry.board) {
  deliverPiToolResults(entry.board, context);
  attachPiStream(entry.activeTurn!, stream);
  return;
}

// New user turn.
if (entry.activeTurn && entry.activeTurn.phase !== "idle") {
  entry.activeTurn.consumerAbort.abort();
  entry.board?.rejectAll("superseded by new pi-tools turn");
  entry.activeTurn = null;
}
```

Shared error boundary in BOTH modes:
```ts
} catch (error) {
  const reason: "aborted" | "error" = options?.signal?.aborted ? "aborted" : "error";
  output.stopReason = reason;
  output.errorMessage = error instanceof Error ? error.message : String(error);
  if (reason === "error") {
    lastError = output.errorMessage;
    if (entryRef) void destroyEntry(entryRef);   // aborts KEEP the pooled session
  }
  stream.push({ type: "error", reason, error: output });
  stream.end();
}
```

**Flow:** resolve caller runtime → pick mode → get/create pool entry (mode is part of the pool key) → pi-tools: continuation delivers tool results into hanging handlers and re-attaches the NEW host stream to the SAME turn state; non-idle turn gets aborted + board-rejected ("superseded"); fresh turn begins `usage.beginTurn`, pushes start, prepends pending preamble + steer text, launches `runPiToolsConsumer`. Agent mode: translate loop over `session.stream(...)` events, then finalize usage and closeOpenBlocks. Errors destroy the entry only for real errors — user aborts keep the session warm.
**Invariant:** A second host stream attaching mid-turn must adopt the existing turn's output (continuation), never fork a second consumer; superseded consumers are aborted and their pending board promises rejected so nothing writes into the abandoned stream; `stream.end()` happens exactly once on every path.
**Probe:** No dedicated upstream suite drives streaming end-to-end (requires Droid subprocess); recorded caveat. Deterministic pins: `src/providers.ts:472-484` continuation/supersede block; error-boundary parity at 533-544 vs 616-625. `test/pi-tools-bridge.test.ts` covers the board plane (next-pass target).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "streamDroidPiTools runPiToolsConsumer isAwaitingPiTools deliverPiToolResults", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt: synchronous-stream-async-driver shape, continuation-vs-supersession gate ordered BEFORE new-turn setup, abort+rejectAll cleanup, and error-only entry destruction. Adapt the MCP/board transport to whatever mechanism suspends your host's tools mid-agent-loop. Omit the Droid steer-prompt copy and ToolSearch allowance.
