<!-- capsule-v2 -->
# Quote verification ladder — how does the server prove (or correct) a model quote against real document text?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do you verify an LLM's citation quotes against extracted source text — tolerating whitespace/case/punctuation drift, page breaks, and ellipses — and what happens to a fabricated quote?

## Three-tier locator + segment splitters + excerpt swap-back
**Path/Symbol:** `backend/src/lib/chat/verifyCitations.ts:32` (`locateQuote`), `:76` (`verifyQuoteAgainstSource`), `:267` (`verifyDocumentCitationAnnotation`), `:200` (`verifyCaseCitationAnnotation`), `:325` (`verifyCitations` batch). Tolerant matching primitive `normalizeWithMap` at `src/lib/chat/tools/documentOps.ts:1678`. Direct test: `src/lib/chat/verifyCitations.test.ts`.
**Signature:** `verifyQuoteAgainstSource(source, quote) -> {verified, needs_correction, start_char?, end_char?, source_excerpt?}`; offsets index into EXTRACTED text, not raw bytes.
**Data Shape:** sentinels — cross-page quotes join segments with `[[PAGE_BREAK]]`; omissions use `...`/`…`; unreadable-source strings ("Document could not be read." / "Document not found.") are treated as no-source, never as match targets.

### Decisive source
```ts
// Tier 1 exact → Tier 2 whitespace+case → Tier 3 +punctuation-stripping.
// normalizeWithMap keeps origIdx[] so the recovered excerpt is the EXACT
// original substring even though matching ran on a lowercased, space-collapsed,
// punctuation-dropped copy ("U.S." collapses to "us", not "u s").
const loc = locateQuote(source, quote);
if (!loc) return { verified: false, needs_correction: false };   // fabricated stays UNVERIFIED
return { verified: true, needs_correction: loc.excerpt !== quote,
         start_char: loc.start, end_char: loc.end, source_excerpt: loc.excerpt };
```

**Flow:** split on PAGE_BREAK / ellipsis first (each segment verified independently; ANY miss ⇒ whole quote unverified) → locate per tier → when matched-with-drift (`needs_correction`) SWAP the exact source excerpt into the displayed quote so the UI never shows drifted text as the source's words → aggregate annotation.verified = AND over all quotes. Batch layer memoizes per-doc source fetch once per turn (`sourceTextByDocId` promise map) with `emitEvents:false` reads; case citations verify against turn-cached opinion text, opinion-scoped when opinionId present.
**Invariant:** Fabricated quotes are marked unverified but PRESERVED verbatim (no silent rewriting of model output); corrections only ever replace drift with the true excerpt. Callers must supply BOTH resolvers (documents + case opinions) so neither citation kind can bypass verification.
**Probe:** `cd backend && bunx vitest run src/lib/chat/verifyCitations.test.ts` (green at pin); targeted greps: `grep -c 'PAGE_BREAK' src/lib/chat/verifyCitations.test.ts` ≥ 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "verifyQuoteAgainstSource locateQuote normalizeWithMap", limit: 10 });
```

## Verdict
Adopt tier-tolerant location with index-map back-mapping + segment splitters mirroring viewer semantics + excerpt swap-back + unreadable-as-unverified; adapt normalization aggressiveness to your extraction pipeline.
