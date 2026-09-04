<!-- capsule-v2 -->
# Native HTML5 drag encoding — zero-width escape hatching for case-sensitive payloads

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Why is the dataTransfer payload base64-wrapped AND case-escaped, and which events must be suppressed for native DnD to coexist?

## DragSensor encode/decode
**Path/Symbol:** `packages/dom/src/core/sensors/drag/encoding.ts:1-23` + `DragSensor.ts:53-168`.
**Signature:** `encode(data): string` = `encodeUpperCase(btoa(JSON.stringify(data)))`; `decode` inverts; MIME type `application/dnd-kit;<payload>` set via `setData(type, ' ')` (empty string is dropped by some browsers).
**Data Shape:** payload `{id, type, rect:{width,height}}`; PREFIX `\u200B\u200C`, SUFFIX `\u200C\u200B` wrap each uppercase run.

### Decisive source
```ts
const PREFIX = '\u200B\u200C';
const SUFFIX = '\u200C\u200B';

function encodeUpperCase(str: string): string {
  return str.replace(/([A-Z]+)/g, `${PREFIX}$1${SUFFIX}`);
}

function decodeUpperCase(str: string): string {
  const escapeRegExp = (escape) => ['', ...escape.split('')].join('\\');
  return str.replace(
    new RegExp(`${escapeRegExp(PREFIX)}(.*?)${escapeRegExp(SUFFIX)}`, 'g'),
    (_, match) => match.toUpperCase()
  );
}
```

**Flow:** dragstart → `stopImmediatePropagation` (hide from other sensors), `clearData`, measure source rect → encode → stash in the MIME TYPE itself (types survive cross-document trips where getData may not) → bind document drag/dragover/dragend. First `drag` event with idle status STARTS the kernel op at pointer coords; subsequent ones move it; dragover preventDefaults and sets `dropEffect='move'`. Cross-window handoff: the receiving window's document-level dragenter reads `event.dataTransfer.types`, finds the dnd-kit entry, decodes.
**Invariant:** base64 output is case-sensitive but browsers LOWERCASE custom MIME types — the zero-width-wrapped uppercase runs preserve case through that mangling (base64 letters re-uppercased after decode of the wrapper); decode failures are swallowed (`catch { no-op }`) because foreign drags can carry spoofed types; handlePointerUp always stops the operation even if the drop was invalid.
**Probe:** live probe executed: round-trip `encode→decode` on `{id:'item-1',type:'card',rect:{width:120.5,height:48}}` returns payload-equal true, encoded string visibly contains zero-width runs; no upstream unit file targets encoding.ts directly (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "encode decode", name_pattern: "^DragSensor$", limit: 10 });
```

## Verdict
Adopt both encodings TOGETHER (either alone breaks); adapt payload fields to your schema; omit DragSensor entirely if you don't need interop with native HTML5 DnD (file drops, OS drags).
