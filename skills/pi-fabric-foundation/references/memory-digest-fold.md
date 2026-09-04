<!-- capsule-v2 -->
# Session digest fold — how do you compress a session into a bounded, hot/cold-tier searchable digest where the vocabulary is capped but structure is never dropped?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what does a memory index keep when a session is too big to index fully, and how does it admit that incompleteness?

## Bounded lexical vocabulary + unbounded structural addresses
**Path/Symbol:** `src/memory/digest.ts:foldSessionDigest` (:57-138); token source `tokenizeLexical` in `src/memory/tokenize.ts:5-8`; privacy gate in `src/memory/normalize.ts` (`DEFAULT_MEMORY_INDEX_PRIVACY` :15-18 — thinking excluded by default).
**Signature:** `foldSessionDigest(input: DigestInput): SessionDigest` with `{maxVocabularyBytes? = MAX_SAFE_INTEGER, filesTouchedLimit? = 50}`.
**Data Shape:** `SessionDigest = {sessionId, file, cwd, firstTs, lastTs, entryCount, filesTouched[], toolHistogram{}, errorCount, vocabulary[] (sorted unique terms), addresses: [index, entryId, operationAddress, role, toolName, timestamp, ref, provider, action, outcome][], indexCoverage: {complete, vocabularyBytes, reasons[]}}`.

### Decisive source
```ts
if (!vocabularyLimitReached) {
  for (const term of tokenizeLexical(entry.text)) {
    if (vocabulary.has(term)) continue;
    const termBytes = Buffer.byteLength(JSON.stringify(term), "utf8")
      + (vocabulary.size === 0 ? 0 : 1);          // + comma; seed estimate = 2 ("[]")
    if (estimatedVocabularyBytes + termBytes > maxVocabularyBytes) {
      vocabularyLimitReached = true;
      break;                       // stop folding terms, KEEP folding entries
    }
    vocabulary.add(term); estimatedVocabularyBytes += termBytes;
  }
}
...
const addresses = input.entries.map((entry) => [entry.index, entry.entryId,
  entry.operationAddress ?? null, /* …typed structural identity per entry… */]);
if (vocabularyLimitReached) reasons.add("max_cold_vocabulary_bytes");
return { ..., indexCoverage: { complete: sortedReasons.length === 0, ... } };
```

**Flow:** one pass over normalized entries accumulates min/max timestamps, error count, tool histogram, first-N unique files, and NFKC-normalized lowercase Unicode lexical terms until the byte budget trips → every entry still contributes its full typed address tuple → coverage reasons (from normalization + `max_cold_vocabulary_bytes`) mark the digest incomplete so search can fall back to cold-session pointer mode instead of pretending completeness.
**Invariant:** lexical truncation is honest and structural retention is total: a size-truncated vocabulary must flip `indexCoverage.complete` to false with a reason; addresses are retained independently of the lexical budget. Terms never contain posting lists (pure vocabulary). Tokenization is canonical (`NFKC`, `\p{L}\p{N}_` runs, lowercased, compared without locale).
**Probe:** `tests/memory-decay.test.ts:122` ("folds exact vocabulary, addresses, files, errors, tools, timestamps, and ranking terms"), `:163` ("returns a cold session pointer instead of entry matches"), `:213` (digest invalidated on source mtime+size change), `:236/:252` (tier reporting + identical mixed-tier recall across runs); `tests/memory-hardening.test.ts:247` ("marks oversized vocabulary and cache-sync budgets incomplete").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "foldSessionDigest SessionDigest vocabulary addresses indexCoverage tokenizeLexical", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-plane digest (capped honest vocabulary + complete structural addresses + explicit incompleteness reasons) for any "index big transcripts" port; adapt budgets and the tier policy; omit pi's normalize carrier types (fabric_operation/branch_fact specifics live in the audit plane).
