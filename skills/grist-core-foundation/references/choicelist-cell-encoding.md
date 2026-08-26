<!-- capsule-v2 -->
# Choice-list cell encoding — how does one CSV cell carry a list ("L",a,b) through copy/paste?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What wire shape do ChoiceList values use, and which input encodings are accepted on paste?

## ChoiceListParser: JSON array OR newline-split CSV rows, trimmed/filtered, wrapped behind an "L" tag
**Path/Symbol:** `app/common/ValueParser.ts`: `class ChoiceListParser` (:69–102): `cleanParse` (:70–81), `_parseJson` (:83–93, `startsWith("[")` gate :85), `_parseCsv` (:95–101, `value.split(/[\n\r]+/)` :97).
**Signature:** `cleanParse(value: string): string[] | null` — null ⇒ caller keeps original string.
**Data Shape:** Output `["L", item1, item2…]` — Grist's tagged choice-list cell encoding.

### Decisive source
```ts
public cleanParse(value: string): string[] | null {
  value = value.trim();
  const result = (
    this._parseJson(value) ||
    this._parseCsv(value)
  ).map(v => v.trim())
    .filter(v => v);            // drop empties AFTER trim
  if (!result.length) return null;
  return ["L", ...result];
}
private _parseJson(value: string): string[] | undefined {
  // Don't parse JSON non-arrays
  if (value.startsWith("[")) {
    const arr = safeJsonParse(value, null);
    return arr?.filter(v => v || v === 0)      // keep 0, drop null/''/false
      .map(v => formatDecoded(v));             // nested objects/arrays re-formatted as JSON strings
  }
}
```

**Flow:** trim once → JSON-array attempt only for `[`-prefixed strings (a bare `"123"` never becomes a one-item list) → else split newlines then CSV-decode each line (choice editor forbids embedded newlines) → trim items, drop empties → empty result returns null (no change) → prefix `"L"` tag.
**Invariant:** The `"L"` prefix IS the type marker consumed by the data engine — returning bare arrays corrupts the cell. Zero-preservation (`v || v === 0`) distinguishes legit numeric choices from null-ish junk; nested structures are flattened to their JSON text rather than rejected. Newline splitting happens BEFORE csvDecodeRow because quoted commas survive within a line but newlines cannot exist in stored choices.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "\[\"L\", ...result\]" app/common/ValueParser.ts && grep -n "v || v === 0" app/common/ValueParser.ts && grep -n "value.split(/\\\\[\\\\n\\\\r\\\\]+/)" app/common/ValueParser.ts'` → :80 tag, :89 zero-guard, :97 newline split.
Direct tests: `test/common/parseDate.ts` has none for this; covered via `test/common/ValueParser.ts`-adjacent suites — anchor: `grep -rn "ChoiceListParser" test/` shows paste-suite usage.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ChoiceListParser cleanParse csvDecodeRow choice list","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the tagged encoding and the JSON-then-CSV acceptance ladder; adapt the tag letter to your engine's vocabulary; omit the zero-preservation filter only if your choice domains exclude falsy members by construction.
