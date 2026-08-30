<!-- capsule-v2 -->
# Mutation-target search labeling — every search result line carries the target its mutation must use, and wrong-target mutations name where the entry lives

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** A model reads `memory_search` output and then calls `memory_remove` with the WRONG target — how do you make the round-trip self-correcting at both ends?

## memory_search labels + addWrongTargetHint
**Path/Symbol:** `src/tools/memory-search-tool.ts` — `mutationTarget` (:17–21: project-scoped ordinary memories display as `"project"`; failures STAY `"failure"` even when project-attributed), `scopeLabel` (:23–25, `project:<encodeURIComponent(name)>` or `global`), output line format :82–85; tool description now states "The displayed target is the value required by memory_replace and memory_remove." `src/tools/memory-tool.ts` — `matchingMutationTargets` (:75–87), `addWrongTargetHint` (:89–105), applied after every non-add action (:372–374). Consumer side: two new prefix-strip ladders in `src/store/memory-lookup.ts` (:11–22).
**Signature:** `addWrongTargetHint(result: MemoryResult, rawTarget, oldText, store, projectStore): MemoryResult`; result gains `matching_targets?: Array<"memory"|"user"|"failure"|"project">` (`src/types.ts`).
**Data Shape:** result line = `emoji scope=<label> [target=<t>][ [category]] <content>\n   Created: … | Last used: …`.

### Decisive source
```ts
// memory-search-tool.ts — project-scoped memory displays as "project", but a
// project-attributed FAILURE still mutates through the failure store:
return entry.target === "memory" && entry.project ? "project" : entry.target;

// memory-tool.ts — only for "No entry matched" failures, probe ALL stores:
const alternatives = matchingMutationTargets(oldText, store, projectStore)
  .filter((target) => target !== rawTarget);
if (alternatives.length === 0) return result;
return { ...result,
  error: `No match in target "${rawTarget}"; matching entry found in ${noun} ${quotedTargets}. `
       + `Retry with the displayed target.`,
  matching_targets: alternatives };

// memory-lookup.ts — pasted lines are stripped BEFORE matching, both shapes:
normalized.replace(/^\S+\s+scope=(?:global|project:[^\s]+)\s+\[target=(?:memory|user|project|failure)\]\s+/u, "");
normalized.replace(/^\[target=(?:memory|user|project|failure)\]\s+/u, "");
```

**Flow:** search renders machine-checkable target labels with URL-encoded scopes (brackets in project names cannot terminate the token) → model copies a whole line into replace/remove → `normalizeMemoryLookupText` strips emoji + scope + target prefixes (and legacy `[global]`/doubled-label forms) so the paste matches → if the model still aimed at the wrong store, the error names the correct one(s) as data (`matching_targets`) instead of a bare failure.
**Invariant:** displayed target === accepted mutation target is the contract that makes copy-paste safe; the display mapping is NOT the storage mapping (`project` exists only in tool space — SQLite stores it as scoped `memory`). Wrong-target hints fire ONLY on genuine no-match errors (never on other failures), never suggest the already-tried target, and keep the original failure semantics when nothing matches anywhere.
**Probe:** `npx tsx --test tests/tools/memory-search-tool.test.ts` — "labels every result with its mutation target and unambiguous scope" (:46, all five scope×target combinations incl. `scope=project:project-a [target=failure]`), "keeps copied results reversible when a project name contains brackets" (:69, `scope=project:foo%5D%20bar` + `normalizeMemoryLookupText(line)` returns the bare content). `npx tsx --test tests/tools/memory-tool.test.ts` — "reports the matching target when remove is sent to the wrong target" (:150, failure-store entry targeted at "memory" ⇒ `/No match in target "memory"/`, `matching_targets === ["failure"]`). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "mutationTarget scopeLabel addWrongTargetHint matchingMutationTargets normalizeMemoryLookupText", limit: 5 })`

## Verdict
Adopt end-to-end label/lookup symmetry: whatever identifiers the read path prints, the write path must accept verbatim. Adapt label grammar to your tools. Pair with `memory-lookup-normalization.md` (the pre-existing strip ladder this extends) and `memory-search-tool-surface.md`.
