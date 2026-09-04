<!-- capsule-v2 -->
# Minimal CSV row codec — what does quoting/decoding mean when CSV is only the paste wire-format?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Exactly which characters trigger quoting, how are edge commas decoded, and why trim unquoted fields?

## csvEncodeCell quotes on [,\r\n"] OR leading/trailing whitespace; decode recovers empty edge fields via delimiter-position check
**Path/Symbol:** `app/common/csvFormat.ts`: whole file (38L): `csvEncodeRow` (:17–19, `prettier` → ", "), `csvDecodeRow` (:21–30), `csvEncodeCell` (:32–34), `csvDecodeCell` (:36–38).
**Signature:** `csvDecodeRow(text: string): string[]`.
**Data Shape:** Excel-like encoding ONLY: `"..."` wrapping, quotes doubled.

### Decisive source
```ts
export function csvDecodeRow(text: string): string[] {
  // Clever regexp from https://github.com/micnews/csv-line
  const parts = text.split(/((?:(?:"[^"]*")|[^,])*)/);
  const main = parts.filter((_, idx) => idx % 2).map(csvDecodeCell);
  // The "delimiter" (odd-numbered parts) is our content. If it's not at the start/end,
  // it means we have commas, and should include empty fields at those ends.
  if (parts[0]) { main.unshift(""); }
  if (parts[parts.length - 1]) { main.push(""); }
  return main;
}
export function csvEncodeCell(value: string): string {
  return /[,\r\n"]|^\s|\s$/.test(value) ? '"' + value.replace(/"/g, '""') + '"' : value;
}
export function csvDecodeCell(value: string): string {
  return value.trim().replace(/^"|"$/g, "").replace(/""/g, '"');
}
```

**Flow:** split with a CAPTURING group so even indexes are separators and odd are fields → leading/trailing non-empty separator pieces prove the row started/ended with a comma → those become explicit "" fields (the classic `a,,b` / `,x` / `x,` preservation trick). Encoding quotes any field containing comma/quote/newline OR outer whitespace; decoding trims unquoted fields so both `a,b` and `a, b` parse identically.
**Invariant:** The whitespace-quote rule pairs with decode-side trimming — dropping either half breaks round-trips for values like `" x "`. The regex accepts quoted fields containing ANY character including newlines? No — rows here are LINE units (callers split lines first); embedded newlines must be encoded but reach this codec already split. Empty-string round-trip: encode("") stays "", decode yields [""] via the trailing-separator push — callers relying on [""] vs [] distinction (choice-list empties) depend on it.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && sed -n "21,30p" app/common/csvFormat.ts | grep -c "parts\[parts.length - 1\]\|parts\[0\]" && sed -n "6p" test/common/csvFormat.ts'` → 2 edge-field guards; test title line "should encode/decode csv values correctly".
Direct tests: `test/common/csvFormat.ts` :6 cell cases, :24 row cases (incl. empty-field edges).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"csvEncodeRow csvDecodeRow csvFormat quote","limit":4,"detail":"ids"}'
```

## Verdict
Adopt byte-for-byte — it's 38 lines whose edge behavior (empty edge fields, whitespace quoting) IS the contract; adapt nothing without re-running its spec; omit the prettier option if you have no human-facing encoder.
