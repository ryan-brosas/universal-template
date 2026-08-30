<!-- capsule-v2 -->
# Memory lookup normalization — pasted tool-output lines are canonicalized before every match, and multi-match refusal is the contract (one deliberate exception for scoped failure copies)

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** Models paste `memory_search` result lines back into edit operations — how do you match old_text robustly WITHOUT ever guessing which entry the model meant?

## normalizeMemoryLookupText
**Path/Symbol:** `src/store/memory-lookup.ts` (whole file, 15 L): trim → collapse to FIRST non-empty line → strip a leading `` ^\S+\s+\[[^\]]+\]\s+ `` prefix (emoji + project label of rendered search output) → dedupe a doubled identical bracket label via backreference `` ^(\[[^\]]+\])\s+\1(\s+|$) ``.
**Signature:** `normalizeMemoryLookupText(text: string) → string`; consumed at `src/store/memory-store.ts` (:367 mutation plan, :418 replace, :466 remove) and `src/store/sqlite-memory-store.ts` (:548, :619).
**Data Shape:** empty/whitespace input normalizes to `""` which callers treat as a hard validation error (`old_text cannot be empty`) — normalization is also the emptiness gate.

### Decisive source
```ts
// memory-store.ts:430-436 / :472-478 — the refusal is the contract
const matches = entries.filter((e) => this.stripMetadata(e).includes(oldText));
if (matches.length === 0) return { success: false, error: `No entry matched '${oldText}'.` };
if (matches.length > 1 && !this.areDistinctScopedFailureCopies(target, matches)) {
  return { success: false, error: `Multiple entries matched '${oldText}'. Be more specific.`,
           matches: matches.map((e) => this.stripMetadata(e).slice(0, 80) + "…") };
}
```
```ts
// memory-store.ts:580-588 — the ONLY ambiguity allowed: N failure entries with
// IDENTICAL visible text but DISTINCT project scopes
private areDistinctScopedFailureCopies(target, entries): boolean {
  if (target !== "failure") return false;
  const visibleTexts = new Set(entries.map((entry) => this.stripMetadata(entry)));
  const scopes = new Set(entries.map((entry) => this.decodeEntry(entry).project));
  return visibleTexts.size === 1 && scopes.size === entries.length;
}
```

**Flow:** normalize → substring match against metadata-stripped entry text (so `<!-- created=… -->` comments never block matching) → 0 matches ⇒ typed error; >1 match ⇒ typed error with an 80-char preview list UNLESS the scoped-failure predicate holds, in which case ALL copies are edited in one pass preserving each scope. The same ladder runs inside the atomic mutation plan (:367–377) so a plan referencing ambiguous old_text fails BEFORE any draft publishes.
**Invariant:** normalization strips RENDER artifacts (search-line prefixes), never user content — it must stay idempotent on already-clean text or legit entries stop matching. The multi-match refusal exists because substring matching over a whole entry list is inherently ambiguous; widening it to "pick the first" silently corrupts memory. The failure exception is safe ONLY because scope (project) disambiguates what text cannot.
**Probe:** `tests/store/memory-store.test.ts` — "accepts a pasted memory_search line for normal memories" (:560) and for failure memories (:575), "returns error when no match found" (:596), the Multiple-entries assertion inside "rejects invalid plans before publishing any draft" (:985/:995); `tests/store/sqlite-memory-store.test.ts` — "normalizes pasted memory_search lines during replace/remove matching" (:289/:307).
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "normalizeMemoryLookupText areDistinctScopedFailureCopies stripMetadata", limit: 5 })`

## Verdict
Adopt for any store whose ids are natural-language substrings authored by an LLM. Adapt the prefix grammar to your own renderer's output format; keep normalize-then-refuse-on-ambiguity and the visible-text+scope identity rule. Omit nothing.
