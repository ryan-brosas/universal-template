<!-- capsule-v2 -->
# Yjs mark surgery — how do you add/remove/update a text mark server-side without ProseMirror's fragment writer?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How are comment marks applied to arbitrary Yjs ranges (and cleaned up by attribute) directly on Y.XmlText, bypassing updateYFragment?

## RelativePosition resolution + manual delta walk
**Path/Symbol:** `apps/server/src/collaboration/yjs.util.ts`:`setYjsMark` / `applyMarkToYFragment` / `removeYjsMarkByAttribute` / `updateYjsMarkAttribute` (lines 15–95, 101–177).
**Signature:** `setYjsMark(doc: Document, fragment: Y.XmlFragment, yjsSelection: YjsSelection, markName: string, markAttributes: Record<string,any>): void`; `updateYjsMarkAttribute(fragment, markName, findByAttribute: {name,value}, newAttributes): void`.
**Data Shape:** `YjsSelection = { anchor, head }` — JSON-encoded Y.RelativePosition (survives concurrent edits), NOT plain integers.

### Decisive source
```ts
const anchorRelPos = Y.createRelativePositionFromJSON(yjsSelection.anchor);
const headRelPos = Y.createRelativePositionFromJSON(yjsSelection.head);
const anchor = relativePositionToAbsolutePosition(doc, fragment, anchorRelPos, mapping);
const head = relativePositionToAbsolutePosition(doc, fragment, headRelPos, mapping);
if (anchor === null || head === null) throw new Error('Could not resolve Y.js relative positions to absolute positions');
```
The walker counts each XmlElement as +1 open tag and +1 close tag while descending (`pos++; ...children...; pos++;`) and skips formatting inside code blocks:
```ts
if (itemEnd > from && pos < to && parentNodeName !== 'codeBlock') {
  item.format(formatFrom, formatLength, { [markName]: markAttributes });
}
```

**Flow:** decode two relative positions → resolve against the CURRENT doc (null = range was deleted ⇒ hard error) → order min/max → walk the fragment accumulating offsets → format overlapping XmlText slices. Removal/update variants iterate `toDelta()`, match on an attribute value (e.g. commentId), then format with `{markName:null}` or merged attrs.
**Invariant:** positions must be RELATIVE (JSON form) — integer offsets computed client-side would land wrong after concurrent edits. Mark removal is `format(..., { [markName]: null })`, not delete. The walker must count element tags as single positions or every offset after the first nested node drifts.
**Probe:** `grep -cF '{ [markName]: null }' apps/server/src/collaboration/yjs.util.ts` (=1), `grep -cF "parentNodeName !== 'codeBlock'" apps/server/src/collaboration/yjs.util.ts` (=1), `grep -cF '// Opening tag' apps/server/src/collaboration/yjs.util.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "setYjsMark applyMarkToYFragment relativePosition format", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt RelativePosition round-tripping + direct XmlText.format for any server-side annotation scheme; adapt the mark name/attribute filter; omit the tiptap schema specifics. No upstream direct test; pinned by source read + probes.
