<!-- capsule-v2 -->
# Process lifecycle + shutdown ladder — how does a stdio child runtime boot, refuse work while dying, and crash honestly?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter embedding an agent runtime as a spawned child process must wire circular stdin/stdout dependencies, order shutdown, and decide what a crash looks like to the host.

## main.ts wiring + RuntimeService shutdown gate
**Path/Symbol:** `agent-runtime/src/main.ts` (:1-39, whole file); `RuntimeService.handle` shutdown gate (service.ts :43-45), `shutdown` (:266-271), `initialize` handshake (:71-83).
**Signature:** `shutdown(): Promise<JsonValue>` returning `{shutdown:true}`; handshake reply `{protocolVersion:1, runtimeVersion, rssBytes}`.
**Data Shape:** Error code `-32003 "Runtime is shutting down"` for every host method except `runtime.shutdown` once the flag flips.

### Decisive source
```ts
let peer: NdjsonRpcPeer;                       // declared BEFORE the engine closure
const engine = new OpenAIAgentsEngine(async (input) =>
  peer.request("tool.invoke", {...}, input.sessionId, input.runId, input.signal));
const service = new RuntimeService(engine);
peer = new NdjsonRpcPeer(process.stdin, process.stdout,
  (request) => service.handle(request));       // circular wiring is safe because
service.attach(peer);                          // the closure fires only after listen()
peer.listen();

process.on("SIGTERM", () => { void engine.shutdown().finally(() => process.exit(0)); });
process.on("uncaughtException", (error) => {
  process.stderr.write(`Clovy agent runtime fatal error: ${errorMessage(error)}\n`);
  process.exit(1);                             // sanitized message only; stderr, never stdout
});
// handle(): if (this.shuttingDown && request.method !== "runtime.shutdown")
//   throw new ProtocolError(-32003, "Runtime is shutting down");
// shutdown(): flag first → abort EVERY active controller → await engine.shutdown()
```

**Flow:** boot = construct engine with a lazy host-tool closure → build peer over raw stdin/stdout → attach + listen; no port, no handshake beyond `runtime.initialize` (replies protocolVersion/runtimeVersion/`rssBytes: process.memoryUsage().rss`, which the host can use as a liveness/pressure signal). Graceful stop: RPC or SIGTERM flips `shuttingDown`, aborts every active run controller (their runs settle as `run.cancelled`), awaits engine teardown, then exits 0. Unrecoverable error: one sanitized line on **stderr** and exit 1 — stdout stays a pure protocol channel so a crashed frame can never be half-parsed by the host.
**Invariant:** The engine→peer reference resolves lazily (TDZ-safe) because tool callbacks cannot fire before `listen()`; during shutdown exactly one method remains legal (`runtime.shutdown` itself) and everything else fails loud with -32003 rather than hanging; abort-before-await ordering means no run outlives the flag; fatal paths write only to stderr and always exit nonzero.
**Probe:** Coverage caveat — NO direct test drives SIGTERM, uncaught handlers, or the shutdown RPC at this pin; only `FakeEngine.shutdown` exists (service.test.ts :478). Claims are source-confirmed from main.ts/service.ts whole-file reads; treat live signal behavior as unproven until target #1's runner upgrade.

## Get live surrounding code
**Retrieve:** executed at pin:
```
search_graph({ project:"os-clovy", query:"shutdown shutting down abort active runs peer close", file_pattern:"agent-runtime/*" })
→ src.transport.NdjsonRpcPeer.close Method transport.ts 105-113           (rank 1)
   src.service.RuntimeService.shutdown Method service.ts 266-271
   src.sdk-engine.OpenAIAgentsEngine.shutdown Method sdk-engine.ts 209-211
```

## Verdict
Adopt lazy-closure wiring for circular peer/engine references, flag-first-then-abort shutdown with a single surviving method, and stderr-only fatal reporting with exit-code honesty. Adapt the signal set and the handshake fields to your supervisor. Omit nothing structural — routing fatal errors through stdout (the protocol channel) is the classic wrong port: it corrupts the frame stream precisely when the process is dying.
