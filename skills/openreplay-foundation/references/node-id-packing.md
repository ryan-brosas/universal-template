<!-- capsule-v2 -->
# Node id packing (level/order/node 22-bit) — how are cross-domain iframe node ids allocated without collisions?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What bit layout must a porter copy so child-frame nodes never collide with top-document ids?

## 2|7|22 bit fields, `v >>> 0` unsigned result
**Path/Symbol:** `tracker/tracker/src/main/app/nodes/idSeq.ts` (:1–31 whole file), consumer `Nodes.crossdomainMode` (`nodes/index.ts:31–33,63–65`) and `TopObserver.crossdomainObserve` (:293 `this.app.nodes.crossdomainMode(frameLevel, frameOder)`).
**Signature:** `pack(level, order, nodeId): number`; `unpack(id): {level, order, nodeId}`.
**Data Shape:** BITS_LEVEL=2 (max 4 nesting), BITS_ORDER=7 (128 frames/level), BITS_NODE=22 (~4.19M usable of 8_388_608 claimed); shifts 22 and 29; RangeError on overflow.

### Decisive source
```ts
export function pack(level: number, order: number, nodeId: number): number {
  if (level < 0 || level > MASK_LEVEL) throw new RangeError('OR: nesting level overflow, max 4')
  ...
  const v = ((level & MASK_LEVEL) << SHIFT_LEVEL)
          | ((order & MASK_ORDER) << SHIFT_ORDER)
          | (nodeId & MASK_NODE)
  return v >>> 0
}
```

**Flow:** top document allocates sequential ids from 0; when a cross-domain child frame joins, the parent computes the frame element's node id, then the child re-bases its counter to `pack(level, frameOrder, 0)` so every subsequent id sits in that frame's band. Player unpacks to reconstruct hierarchy.
**Invariant:** Sequential ids must NEVER be reset mid-session except via `clear()` — cross-domain rebasing happens once per frame at start. The `>>> 0` keeps ids positive under bitwise ops.
**Probe:** `grep -c 'BITS_NODE  = 22' tracker/tracker/src/main/app/nodes/idSeq.ts` → `1`; `grep -c 'v >>> 0' tracker/tracker/src/main/app/nodes/idSeq.ts` → `1`; `grep -c 'crossdomainMode(frameLevel, frameOder)' tracker/tracker/src/main/app/observer/top_observer.ts` → `1`; direct tests `tests/nodes.unit.test.ts` executed green.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "idSeq pack unpack crossdomainMode frame", limit: 10 });
```

## Verdict
Adopt field-packed ids for multi-context capture. Adapt widths. Omit if single-document only.
