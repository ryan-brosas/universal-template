<!-- capsule-v2 -->
# CE no-op realtime shell — why does the open-source build ship a socket class whose every method is empty?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How do dozens of service-layer broadcast calls survive in a build with NO websocket server at all?

## Semantic-stub seam for EE override
**Path/Symbol:** `packages/nocodb/src/socket/NocoSocket.ts` (whole 17L) and `packages/nocodb/src/socket/NocoPresence.ts` (whole 8L).
**Signature:** static `handleConnection/broadcastEvent/broadcastDataEvent/broadcastBulkDataEvent/broadcastEventToBaseUsers/broadcastEventToWorkspaceUsers/broadcastEventToUser(...)` all no-op; NocoPresence: `setupHandlers(_socket)`, `handleDisconnect(_socket, _ioServer)` no-ops.
**Data Shape:** zero state; callers pass full payloads that are silently discarded.

### Decisive source
```ts
export default class NocoSocket {
  public static ioServer;

  public static handleConnection(..._args: unknown[]) {}

  public static broadcastEvent(..._args: unknown[]) {}
  public static broadcastDataEvent(..._args: unknown[]) {}
  public static broadcastBulkDataEvent(..._args: unknown[]) {}
  public static broadcastEventToBaseUsers(..._args: unknown[]) {}
  public static broadcastEventToWorkspaceUsers(..._args: unknown[]) {}
  public static broadcastEventToUser(..._args: unknown[]) {}
}
```
(whole file)

**Flow:** services (comments, grid-columns, bases, views, filters, columns, forms, extensions — every mutation path) call `NocoSocket.broadcastEvent(...)` fire-and-forget → CE resolves to the stub, so calls compile and run but emit nothing; the EE build swaps in a real implementation with identical signatures (same doctrine as ce-stub-parity-trace: keep FULL types so override sites never touch call code).
**Invariant:** call-site code must be identical across editions — the stub's value is preserving the exact API SHAPE. Underscore-prefixed params (`_args`, `_socket`) mark intentionally-unused parameters so linters stay quiet without weakening signatures. Do NOT "optimize" these away or wrap them in conditionals; presence handling rides the same pattern.
**Probe:** `cd packages/nocodb && grep -c "broadcastEvent" src/socket/NocoSocket.ts` (=4: data/dataBulk/baseUsers variants included via substring) and `grep -rln "NocoSocket.broadcastEvent" src/services --include="*.ts" | wc -l` (=34 consumer service files at pin).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "NocoSocket broadcastEvent NocoPresence setupHandlers", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt signature-preserving no-op shells wherever an edition/tenant split needs silent degradation; adapt the method set to your event vocabulary; omit if you ship one fully-featured build. Coverage caveat: grep-pinned only.
