<!-- capsule-v2 -->
# Session-keyed toggle tools — how do per-session background streams (logging, subscription updates) get switched on and off idempotently when `sessionId` may be undefined?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** What is the state discipline for a tool that toggles a server-side per-session behavior, given stdio sessions have no session id?

## Module-level Set keyed by raw sessionId; toggle = membership check + start/stop pair
**Path/Symbol:** `src/everything/tools/toggle-simulated-logging.ts` (whole file, 60L: clients Set :22–23; handler :38–58) and its structural twin `src/everything/tools/toggle-subscriber-updates.ts` (whole file, 63L — same shape over `beginSimulatedResourceUpdates`/`stopSimulatedResourceUpdates`). Backends live in `server/logging.ts` (`beginSimulatedLogging` :16, `stopSimulatedLogging` :75) and `resources/subscriptions.ts` (:139/:164) — stream mechanics covered by `logging-stream-contract.md` / `resource-subscription-fanout.md`.

**Signature:** handler reads `const sessionId = extra?.sessionId;` — deliberately UNCOERCED. `clients: Set<string | undefined>` includes `undefined` as a legitimate key so the stdio singleton session toggles like any other.

**Data Shape:** Set membership IS the state store; no TTL, no persistence (demo scope). Both twins keep SEPARATE Sets — logging and updates toggle independently.

### Decisive source
```ts
// toggle-simulated-logging.ts:38-58 — read extra.sessionId RAW, branch on membership
async (_args, extra): Promise<CallToolResult> => {
  const sessionId = extra?.sessionId;
  let response: string;
  if (clients.has(sessionId)) {
    stopSimulatedLogging(sessionId);
    clients.delete(sessionId);
    response = `Stopped simulated logging for session ${sessionId}`;
  } else {
    beginSimulatedLogging(server, sessionId);
    clients.add(sessionId);
    response = `Started simulated, random-leveled logging for session ${sessionId} ...`;
  }
  return { content: [{ type: "text", text: `${response}` }] };
}
```

**Flow:** invoke → membership probe on the RAW session key → active ⇒ stop backend + delete + report stopped; inactive ⇒ start backend + add + report started → next invoke flips again (true toggle, not set-once).

**Invariants:**
1. **Never coerce or default `extra?.sessionId`** before the membership check: normalizing undefined to a sentinel string in ONE place but not the other desynchronizes the two code paths; `undefined` is a valid stdio-session key precisely because BOTH the add and has sides treat it uniformly.
2. **The Set is the single source of truth** — don't derive "is it running?" from timer existence or backend internals; backends are started/stopped symmetrically by the same key.
3. **Independent concerns get independent sets** — merging the two features into one registry couples unrelated client choices.
4. The response text doubles as the audit surface (session id echoed both ways).

**Probe:** `src/everything/__tests__/tools.test.ts:467–534` — start-when-inactive, stop-when-active, AND `should handle undefined sessionId` pins the uncoerced-key invariant for the logging twin; :506–534 repeats start/stop for updates. Coverage caveat: no test drives the two toggles' independence explicitly (deterministic source probe :22–23 separate Sets).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "toggle simulated logging subscriber updates sessionId clients Set", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt raw-keyed membership Sets with symmetric start/stop for any per-session feature switch; adapt to a TTL/LRU map in multi-tenant hosts (dead sessions leak entries here); omit the demo interval messaging. Complements the fanout/logging capsules which own the STREAM side.
