<!-- capsule-v2 -->
# Compaction bounds — UTF-8-safe clipping, canonicalization, provenance-preserving sampling

**Source:** pi-fabric (monotykamary) MIT `<branch>@<commit>`; Codebase Memory `pi-fabric`. **Question:** how does context compaction clip/canonicalize/sample text within byte budgets without splitting UTF-8 or losing provenance?

## Connected graph-selected seam
**Path/Symbol:** `src/compaction/bounds.ts` (102 lines): `MAX_SUMMARY_BYTES = 32*1024` (:1), `utf8Bytes` (:6), `clipUtf8` (:8-23), `canonicalizeText` (:31-39), `sampleAddressedFrom` (:53-85), `omissionLine` (:92-102).
**Signature:** `clipUtf8(text, maxBytes, suffix="…")` — iterates characters (code points) accumulating UTF-8 bytes up to `maxBytes - suffixBytes`, appends the suffix; `canonicalizeText` — trims + collapses whitespace, clips to `MAX_REQUEST_SOURCE_BYTES` (8KB); `sampleAddressedFrom` — keeps earliest `ceil(max/2)` + latest `floor(max/2)` entries, tracks omitted count + first/last omitted entryIds.
**Data Shape:** `CanonicalText {text, truncated, sourceBytes}`; `AddressedSample {values, omitted, omittedFirstEntryId?, omittedLastEntryId?, splitIndex}`; `AddressedValue {entryId}`.

### Decisive source
```ts
export const clipUtf8 = (text, maxBytes, suffix = "…") => {
  if (utf8Bytes(text) <= maxBytes) return text
  const suffixBytes = utf8Bytes(suffix)
  const available = maxBytes - suffixBytes
  for (const character of text) {           // iterate code points, never split UTF-8
    const bytes = utf8Bytes(character)
    if (used + bytes > available) break
    output += character; used += bytes
  }
  return `${output}${suffix}`
}
export const sampleAddressedFrom = (source, maxValues) => {
  // earliest ceil(max/2) + latest floor(max/2); displaced entries counted as omitted
  // with omittedFirstEntryId / omittedLastEntryId tracked (provenvenance preserved)
}
export const omissionLine = (count, firstEntryId, lastEntryId, noun) =>
  `… omitted ${count} ${noun}; source entries ${firstEntryId} → ${lastEntryId}`
```

**Flow:** clip iterates code points so a multi-byte UTF-8 char is never split; canonicalize collapses whitespace then clips; sample keeps both ends (earliest + latest) with an explicit omitted range so a reader knows what was dropped.
**Invariant:** clipping never splits a UTF-8 code point; sampling preserves provenance (omitted first/last entryIds); summaries bounded at `MAX_SUMMARY_BYTES` (32KB).
**Probe:** `tests/compaction.test.ts` + `compaction-qa.test.ts` (clipUtf8 keeps a code point whole; canonicalize collapses whitespace; sampleAddressedFrom keeps earliest+latest and tracks omitted range).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "clipUtf8 canonicalizeText sampleAddressedFrom omissionLine compaction bounds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the UTF-8-safe clip, whitespace-collapsing canonicalize, and earliest+latest provenance-preserving sample; adapt the byte budgets to host.
