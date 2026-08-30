<!-- capsule-v2 -->
# Skill modal sort grammar — three-mode comparator with null-last dates and fixed category tie-break

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** A TUI list mixes managed records (with dates) and read-only externals (often dateless) — how does one deterministic comparator serve three user-facing sort modes without ever scattering rows unpredictably?

## Modal row model & sort grammar
**Path/Symbol:** `src/handlers/skills-command.ts` — `compareSkillRows` (:195–231), `recencyValue` (:169–171), `categoryOrder` (:158–167), `nextSortMode`/`sortModeLabel` (:173–193), `buildSkillRows` (:326–347), `buildUnifiedSkillRows` (:349–383), `collectLoadedSkillsFromCommands` (:233–267), `createExternalSkillId` (:143–150), `normalizePathForKey` (:122–126), `formatSkillPath` (:128–137).
**Signature:** `compareSkillRows(a: SkillModalRow, b: SkillModalRow, sortMode: "updated"|"created"|"name"): number`; `buildUnifiedSkillRows(managed: SkillIndex[], loaded: LoadedSkillRow[], selectedIds?, sortMode?) → SkillModalRow[]`.
**Data Shape:** `SkillModalRow` = { skillId, scope?, category: "G"|"P"|"E", mutable, name, displayName, description, path, displayPath, created?, updated?, projectName?, selected, searchText }. External id = `external:<safeName>:<sha1(name|path).slice(0,10)>`.

### Decisive source
```ts
// compareSkillRows (195-231): mode → primary → secondary → FIXED tail
if (sortMode === "name") {
  const byName = a.displayName.localeCompare(b.displayName);
  if (byName !== 0) return byName;
  return categoryOrder(a.category) - categoryOrder(b.category);
}
const primaryA = sortMode === "updated" ? recencyValue(a) : (a.created || "");
...
if (primaryA || primaryB) {
  if (!primaryA) return 1;                    // DATELESS ROWS SINK — never NaN-compare
  if (!primaryB) return -1;
  if (primaryA !== primaryB) return primaryB.localeCompare(primaryA); // ISO strings: desc via string compare
}
if (sortMode === "updated") { /* secondary = created desc, same null-last ladder */ }
else                        { /* secondary = updated desc */ }
const byCategory = categoryOrder(a.category) - categoryOrder(b.category); // G=0 P=1 E=2 always
return a.displayName.localeCompare(b.displayName);

// recencyValue: updated || created || ""  — fallback chain, not a merge
function recencyValue(row) { return row.updated || row.created || ""; }

// buildUnifiedSkillRows (349-383): path-key dedupe BEFORE external rows are minted
const managedPathKeys = new Set(managedRows.map(r => normalizePathForKey(r.path)));
for (const loaded of loadedSkills) {
  const loadedKey = normalizePathForKey(loaded.path);
  if (managedPathKeys.has(loadedKey)) continue;   // same file loaded AND managed → managed wins
  if (externalPathKeys.has(loadedKey)) continue;  // duplicate loads collapse
  ...
}
```

**Flow:** (1) `collectLoadedSkillsFromCommands` harvests the host's actually-loaded commands (`source === "skill"`, `skill:` prefix stripped) into read-only rows. (2) `buildUnifiedSkillRows` merges store rows + harvested rows: normalization (`path.resolve`, backslash→slash, lowercase on win32 only) makes the path set the identity for dedupe — a file both managed and loaded appears ONCE as its mutable managed row. (3) The comparator serves all three modes from one function; every mode ends in the SAME category-order then display-name tail, so any two rows have a total, stable order. (4) `nextSortMode` cycles updated→created→name→updated; labels render `[G] [P] [E]` filter chips alongside.

**Invariant:** dateless rows never compare as NaN — missing dates sink to the bottom via explicit `!primaryA → 1` ladders and empty-string sentinels; ISO `YYYY-MM-DD` dates sort correctly under plain `localeCompare`, so no Date parsing is needed anywhere. The dedupe key is the NORMALIZED PATH (not name/skillId), which is what makes the unified view safe: names may collide across roots, but one on-disk file is one row. Category order (global < project < external) is load-bearing beyond sorting — it is also the filter-chip and section-rendering order.

**Probe:** `tests/store/skill-store.test.ts` — `sorts skills by updated date descending, then created date descending` (:268); `tests/handlers/skills-command.test.ts` — unified-row and dedupe cases live in this suite (grep `buildUnifiedSkillRows`). Coverage caveat: `tests/` is excluded from the graph index by design; probes are source-grounded from on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "compareSkillRows sortMode categoryOrder recencyValue", limit: 5 });
// live-verified rank-exact ×3: categoryOrder :158-167, recencyValue :169-171, compareSkillRows :195-231
```

## Verdict
Adopt the single-comparator/three-mode shape with null-last date ladders, ISO-string ordering, and the fixed category tail for any mixed managed+discovered record list. Adapt categories and date formats. Omit the sha1 external-id scheme unless your host lacks stable ids for discovered items.
