<!-- capsule-v2 -->
# Whole-entry replacement guard — refuse a replace() fragment that would silently drop sibling facts from a multi-fact entry

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** `replace()` swaps an ENTIRE §-entry — what stops a model that quotes only the one line it wants to change from silently deleting the entry's other lines?

## MemoryStore.validateWholeEntryReplacement
**Path/Symbol:** `src/store/memory-store.ts:validateWholeEntryReplacement` (:643–661); enforced at BOTH mutation entries — single `replaceUnlocked` (:486–487) and atomic `applyMutationPlan` replace branch (:420–421) — i.e. every replace path funnels through one gate before any draft is published.
**Signature:** `private validateWholeEntryReplacement(entries: string[], oldText: string, newContent: string): string | undefined`.
**Data Shape:** per matched entry: split stripped text into trimmed non-empty lines; if ≤1 line, pass. Otherwise every line must appear in the replacement (line is a substring of `oldText`, or `newContent` includes it); any missing line ⇒ error string naming counts and quoting the exact missing lines.

### Decisive source
```ts
for (const entry of entries) {
  const entryLines = this.stripMetadata(entry).split("\n").map((l) => l.trim()).filter(Boolean);
  if (entryLines.length <= 1) continue;
  const missingLines = entryLines.filter(
    (line) => !line.includes(oldText) && !newContent.includes(line),
  );
  if (missingLines.length > 0) {
    return (
      `Refusing replace: the matched entry has ${entryLines.length} lines, but 'content' ` +
      `does not include ${missingLines.length} of them: ${JSON.stringify(missingLines)}. ` +
      `replace() swaps the WHOLE entry, so 'content' must contain everything you want to ` +
      `keep from it (not just the changed part), or split the entry into separate ` +
      `single-fact entries first.`);
  }
}
return undefined;
```

**Flow:** match entries by lookup text → run the whole-entry check BEFORE building replacement maps → refusal returns `success: false` with disk bytes untouched (the atomic plan validates against its unpublished draft, so nothing was written anyway) → passing content proceeds to encode with original `created` + today's `last` metadata.
**Invariant:** data loss by partial quote must be structurally impossible: the guard's escape hatches are exactly two — include everything you keep, or split the entry first. It is lenient in the right direction (`oldText` itself may span several lines, so any line CONTAINING the match passes) and strict where it matters (every other sibling line must survive verbatim inside `newContent`). Single-line entries are exempt because there is nothing to orphan.
**Probe:** `npx tsx --test tests/store/memory-store.test.ts` — "refuses fragment replacement that would discard sibling facts" (:624, replace `"Name: Cataldo"` → `"Name: Aldo"` on a 3-line entry ⇒ `/Refusing replace/` AND "Arch Linux" still present), "strips metadata from multiline entries and accepts a full replacement" (:636, same old_text but full 3-line content ⇒ success + deep-equal entries), "refuses an atomic fragment replacement that would discard sibling facts" (:1184, plan rejected, on-disk bytes unchanged). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "validateWholeEntryReplacement stripMetadata replaceUnlocked applyMutationPlan", limit: 5 })`

## Verdict
Adopt for any API whose replace primitive is whole-record while callers naturally think line-edit. Adapt the line/entry granularity to your record format. Pair with `memory-mutation-plan.md` (the atomic path sharing this gate) and `memory-store.md` (the §-entry format motivating it).
