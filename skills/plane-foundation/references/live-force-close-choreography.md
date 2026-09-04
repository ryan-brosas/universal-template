<!-- capsule-v2 -->
# Force-close choreography — how do you evict every client of one document across a server fleet and guarantee it leaves memory?

**Source:** plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** What is the safe ordering of notify → close → fan-out → unload when killing a collaborative document everywhere at once, and what does each receiving server do with a command for a document it doesn't hold?

## Seven-step eviction
**Path/Symbol:** `apps/live/src/extensions/force-close-handler.ts:forceCloseDocumentAcrossServers` (:102–202) and `ForceCloseHandler` (:16–89); envelope types in `apps/live/src/types/admin-commands.ts` (:14–68, :73–110).
**Signature:** `forceCloseDocumentAcrossServers(instance: Hocuspocus, pageId: string, reason: ForceCloseReason, code: CloseCode = CloseCode.FORCE_CLOSE): Promise<void>`; handler registered as `onAdminCommand(AdminCommand.FORCE_CLOSE, (data: ForceCloseCommandData) => ...)`.
**Data Shape:** `ForceCloseReason` enum (`critical_error`, `memory_leak`, `document_too_large`, `admin_request`, `server_shutdown`, `security_violation`, `corruption_detected`); custom WS close codes 4000–4003 beside the standard family; wire messages: server→server `ForceCloseCommandData` (command, docId, reason, code, originServer, timestamp), server→client `ClientForceCloseMessage` (`type: "force_close"`, reason, code, message, timestamp).

### Decisive source
```ts
// local: notify first, then close, then hand off to other servers
document.connections.forEach(({ connection }) => {
  try { connection.sendStateless(JSON.stringify(forceCloseMessage)); messageSentCount++; }
  catch (error) { logger.error("[FORCE_CLOSE] Failed to send message to client:", error); }
});
await new Promise((resolve) => setTimeout(resolve, 50));          // delivery grace
// ... close each connection with { code, reason } ...
const receivers = await redisExt.publishAdminCommand(commandData); // cross-server fan-out
const waitTime = 800;
await new Promise((resolve) => setTimeout(resolve, waitTime));    // wait for peers
await instance.unloadDocument(document);
if (instance.documents.get(pageId)) { logger.error("... Document still in memory! ..."); }
```
Receiver side (`ForceCloseHandler.onConfigure`, priority **999**): `const document = instance.documents.get(docId); if (!document) return;` — a server that doesn't hold the doc ignores the command silently.

**Flow:** STEP 1 verify doc exists locally (already-unloaded ⇒ no-op) → STEP 2 send stateless `force_close` JSON to every local connection (per-connection try/catch, count successes) → 50 ms grace → STEP 3 close connections `{code, reason}` → STEP 4 publish `AdminCommand.FORCE_CLOSE` on the admin bus (returns receiver count) → STEP 5 wait 800 ms for peers → STEP 6 `instance.unloadDocument(document)` (unload errors logged, never thrown) → STEP 7 re-check `instance.documents.get(pageId)` and log a loud ❌ if still resident. Human-readable per-reason client strings come from `getForceCloseMessage`.
**Invariant:** Notify-before-close so clients learn WHY the socket dropped; close-code carries the reason machine-readably; unload failures are observable but non-fatal; every step tolerates partial failure (counts sent/closed vs total). The remote handler must ignore foreign docIds — the admin channel is fleet-wide.
**Probe:** No dedicated upstream test. Deterministic pins: force-close-handler.ts contains `priority = 999`, the 50 ms delivery grace as a literal `setTimeout(resolve, 50)` (:69 local handler, :140 choreography), and the peer wait via `const waitTime = 800` → `setTimeout(resolve, waitTime)` (:177–179).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "force close document across servers unload", limit: 5 });
```
Observed at pin: rank-1 = `forceCloseDocumentAcrossServers` (:102–202), rank-2 = `ForceCloseHandler.onConfigure` (:20–88).

## Verdict
Adopt the seven-step choreography, custom-close-code taxonomy, priority-tagged handler extension pattern, and silent-ignore of unheld documents; adapt timings (50 ms/800 ms) and reason enums to your ops needs; omit Plane's specific admin reasons you don't trigger. Coverage caveat: whole-file source reads only; no upstream tests exercise this path.
