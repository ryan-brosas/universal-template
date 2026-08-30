<!-- capsule-v2 -->
# Reference lookup ladder — how does typing a display value ("Ford") become a rowId (42), and what when the table isn't loaded?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What does a ReferenceParser return in each of: blank input, visibleCol=id, table loaded, table NOT loaded, and no match?

## Three-way return: 0 for blanks; ["l", value, {column}] encoded LOOKUP when unloaded; rowId-or-original-string when loaded
**Path/Symbol:** `app/common/ValueParser.ts`: `class ReferenceParser` (:119–160): `parse` (:130–133), `lookup` (:135–159) — blank→0 (:136–138), id-integer coercion (:140–148), deferred `["l", value, options]` (:150–156), `findMatchingRowId || raw` (:158).
**Signature:** `lookup(value: any, raw: string): any`.
**Data Shape:** Lowercase `"l"` = "resolve this lookup server-side"; uppercase `"L"` = literal list. `options = { column: visibleColId, raw?: originalString }`.

### Decisive source
```ts
public lookup(value: any, raw: string): any {
  if (value == null || value === "" || !raw) {
    return 0;  // default value for a reference column
  }
  if (this._visibleColId === "id") {
    const n = Number(value);
    if (Number.isInteger(n)) { value = n; }   // don't return yet — must verify the row EXISTS
    else { return raw; }
  }
  if (!this.tableData?.isLoaded) {
    const options: { column: string, raw?: string } = { column: this._visibleColId };
    if (value !== raw) options.raw = raw;
    return ["l", value, options];
  }
  return this.tableData.findMatchingRowId({ [this._visibleColId]: value }) || raw;
}
```

**Flow:** Blank/empty ⇒ numeric 0 (Grist's "no reference" sentinel, NOT null). When the referenced table's data is present locally, resolve immediately to a positive rowId or hand back the raw STRING (which becomes AltText — visible to the user as unparseable text rather than silently dropped). When absent, emit the lowercase-`"l"` tuple so the DATA ENGINE performs the same resolution with full access.
**Invariant:** The `raw` fallback is deliberate losslessness: an unmatched reference must remain visible/complainable, never vanish into a dangling 0. The `raw` option rides along ONLY when parse changed the value (`value !== raw`) so the engine can retry the original text. Integer coercion happens even before load checks because ids are numbers by construction — but existence is still verified later (engine-side when unloaded).
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "return 0;  // default value for a reference column" app/common/ValueParser.ts && grep -n "\[\"l\", value, options\]" app/common/ValueParser.ts'` → :137 and :155.
Direct tests: reference-paste behavior exercised via `test/server/lib/OpenAIAssistantV1.ts`? No — anchor suite: `grep -rln "ReferenceParser" test/` → paste/import suites.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ReferenceParser findMatchingRowId visibleColParser lookup","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the three-outcome contract (0 / deferred-tuple / rowId-or-string); adapt the sentinel and tag letters to your encoding; omit the raw-carrying option only if your engine never retries alternate forms.
