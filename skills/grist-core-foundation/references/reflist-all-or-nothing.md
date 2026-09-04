<!-- capsule-v2 -->
# RefList all-or-nothing resolution — why does ONE unmatched member invalidate the whole pasted list?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are multi-reference strings resolved, and what preserves user intent when some members match but one doesn't?

## ReferenceListParser resolves every member; ANY miss returns the ENTIRE raw string as AltText
**Path/Symbol:** `app/common/ValueParser.ts`: `class ReferenceListParser extends ReferenceParser` (:162–211): JSON-or-CSV member split (:164–173), id-list fast path (:180–188), unloaded tuple (:190–196), loaded loop with early raw return (:198–209).
**Signature:** `parse(raw: string): any` — outputs `null` (empty), `["l", values[], options]`, or `["L", rowId...]`.
**Data Shape:** Members parsed individually via the inherited `visibleColParser.cleanParse`; non-strings go through `encodeObject`.

### Decisive source
```ts
const rowIds: number[] = [];
for (const value of values) {
  const rowId = this.tableData.findMatchingRowId({ [this._visibleColId]: value });
  if (rowId) { rowIds.push(rowId); }
  else {
    // There's no matching value in the visible column, i.e. this is not a valid reference.
    // We need to return a string which will become AltText.
    return raw;
  }
}
return ["L", ...rowIds];
```

**Flow:** try `JSON.parse` first (arrays survive quoted commas), fall back to `csvDecodeRow(raw)` which cannot throw → each member cleaned via the visible column's own parser → empty list or empty raw ⇒ null → id-column fast path maps all members through Number and requires EVERY one integer else raw → unloaded ⇒ single lowercase tuple carrying the whole array → loaded ⇒ resolve each; one failure aborts to raw.
**Invariant:** ALL-OR-NOTHING: partial lists (`["L", 4, 7]` from "Ford, Toyta") would silently rewrite user data — dropping "Toyta" without trace. Returning the untouched raw string makes the cell AltText, surfacing the typo. Contrast with singular ReferenceParser which has no partial-success case to guard. Empty-input ⇒ null (the RefList default) mirrors ReferenceParser's 0.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && sed -n "198,210p" app/common/ValueParser.ts | grep -n "return raw\|findMatchingRowId" && grep -n "csvDecodeRow should never raise" app/common/ValueParser.ts'` → loop at :199–208 with comment :204–205, throw-safety comment :171.
Direct tests: RefList paste cases live with the paste-suite (`grep -rln "RefList" test/` anchors them).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ReferenceListParser rowIds AltText csvDecodeRow","limit":5,"detail":"ids"}'
```

## Verdict
Adopt all-or-nothing + AltText preservation; adapt tag vocabulary; omit the encodeObject branch only if non-string members cannot reach your paste path.
