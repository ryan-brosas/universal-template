<!-- capsule-v2 -->
# Live server bootstrap & shutdown lifecycle — in what order do redis, hocuspocus, and routes come up, and what must teardown preserve?

**Source:** plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** A porter standing up a multi-instance collaboration service must know which dependency failures abort startup, why the extension array order is a contract, and what graceful shutdown must close first.

## Bootstrap/shutdown ladder
**Path/Symbol:** `apps/live/src/server.ts:Server.initialize/destroy` (:42–55, :106–127), `apps/live/src/hocuspocus.ts:HocusPocusServerManager` (:17–69), `apps/live/src/extensions/index.ts:getExtensions` (:13–19).
**Signature:** `initialize(): Promise<void>`; `destroy(): Promise<void>`; `HocusPocusServerManager.initialize(): Promise<Hocuspocus>`.
**Data Shape:** Express app + express-ws; port/base path from env (`LIVE_BASE_PATH` mount for the router); hocuspocus instance is created once and injected into every controller via `registerController(this.router, controller, [hocuspocusServer])`.

### Decisive source
```ts
public async initialize(): Promise<void> {
  try {
    await redisManager.initialize();
    const manager = HocusPocusServerManager.getInstance();
    this.hocuspocusServer = await manager.initialize();
    this.setupRoutes(this.hocuspocusServer);
    this.setupNotFoundHandler();
  } catch (error) { logger.error("SERVER: Failed to initialize live server dependencies:", error); throw error; }
}
// extensions/index.ts
export const getExtensions = () => [
  new Logger(), new Database(), new Redis(), new TitleSyncExtension(),
  new ForceCloseHandler(), // Must be after Redis to receive broadcasts
];
```

**Flow:** init: Redis connect (ping gate) → HocusPocus singleton (`name = env.HOSTNAME || uuidv4()`, `debounce: 10000`, onAuthenticate/onStateless hooks, extension array) → routes get the instance → listen. destroy: `hocuspocusServer.closeConnections()` → `redisManager.disconnect()` → `httpServer.close()` promise-wrapped. Any init failure logs and rethrows (process refuses half-alive startup); Redis absence is NOT fatal — `RedisManager.connect()` warns "Redis functionality will be disabled" when no URL resolves.
**Invariant:** Extension registration order is load-bearing: ForceCloseHandler must be constructed after Redis because its `onConfigure` looks the Redis extension up in `instance.configuration.extensions` to register the force-close admin command. Startup order guarantees Redis exists before any document handler can need it; shutdown closes WS connections before dropping Redis so cross-server notifications still flush.
**Probe:** No dedicated upstream test (apps/live ships only pdf-export suites). Deterministic pin: `server.ts` contains `await redisManager.initialize();` before `manager.initialize()`; `extensions/index.ts` comment `Must be after Redis`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "HocusPocusServerManager singleton initialize hocuspocus server", limit: 5 });
```
Observed at pin: rank-1..5 all HocusPocusServerManager members + Server.initialize (hocuspocus.ts :40–54/:59–61/:17–69, server.ts :42–55).

## Verdict
Adopt the ordered init ladder with fail-fast rethrow, singleton server manager keyed by hostname-or-uuid, connection-close-before-Redis teardown, and order-documented extension arrays; adapt the Express/express-ws shell and `@plane/*` imports to your host; omit Plane's controller decorator registry and CORS/env specifics as-is. Coverage caveat: all cited paths no_recorded_issue @ gen 2026-08-25T19:59:48Z; behavior claims rest on whole-file source reads (no upstream tests for these files).
