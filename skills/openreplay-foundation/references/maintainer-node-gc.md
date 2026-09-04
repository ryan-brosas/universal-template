<!-- capsule-v2 -->
# Maintainer detached-node GC — how are leaked node registrations from removed iframes/windows reclaimed?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What background sweep safely unregisters dead nodes that MutationObserver teardown missed?

## 30 s interval, batched liveness probe, window-closed detection
**Path/Symbol:** `tracker/tracker/src/main/app/nodes/maintainer.ts` (:1–122 whole file: `processMapInBatches` 50 ms slices, `isNodeStillActive`, defaults `{interval:30s, batchSize:2500, enabled:true}`); registration side `nodes/index.ts` (`registerNode/unregisterNode/cleanTree`).
**Signature:** `Maintainer(nodesMap, unregisterNode, options?)`; `isNodeStillActive(node): [boolean, reason]`.
**Data Shape:** liveness = `node.isConnected && ownerWindow not closed && documentElement connected`; try/catch converts cross-origin access throws into `false`.

### Decisive source
```ts
if (!node.isConnected) return [false, 'not connected']
const nodeIsDocument = node.nodeType === Node.DOCUMENT_NODE
const nodeWindow = nodeIsDocument ? node.defaultView : node.ownerDocument?.defaultView
...
if (nodeWindow.closed) return [false, 'window closed']
```
```ts
// batches of 2500 over 50 ms timeouts keep the main thread responsive
setTimeout(processNextBatch, 50)
```

**Flow:** every 30 s the map is walked in slices; inactive nodes get unregistered (removing listeners + id property). Complements observer-side removal (`unbindTree` handles parent-removal events; UnbindNodes percentage message covers mass iframe swaps >30 %).
**Invariant:** Never unregister a node whose owner window is still open mid-check (race with re-insertion) — the isConnected + closed double-check is the guard. Batch slicing is required: 30 k nodes synchronously freeze the tab.
**Probe:** `grep -c 'window closed' tracker/tracker/src/main/app/nodes/maintainer.ts` → `1`; `grep -c 'batchSize: 2500' tracker/tracker/src/main/app/nodes/maintainer.ts` → `1`; `grep -c '3ms for 30k nodes' tracker/tracker/src/main/app/nodes/index.ts` → `1`; direct tests `tests/nodes.unit.test.ts` executed green.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "Maintainer processMapInBatches isNodeStillActive", limit: 10 });
```

## Verdict
Adopt batched liveness sweep. Adapt thresholds. Omit if your host guarantees full teardown callbacks.
