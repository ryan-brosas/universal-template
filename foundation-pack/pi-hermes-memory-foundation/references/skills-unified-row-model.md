<!-- capsule-v2 -->
# Skills unified row model — one identity space where managed store rows and runtime-loaded external skills collide on normalized paths

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** The skill store owns G/P skills on disk while the host session has separately loaded external skills as slash commands — how do you merge both inventories into one sortable/filterable list without double-listing a skill that exists in both?

## buildUnifiedSkillRows / buildSkillRows
**Path/Symbol:** `src/handlers/skills-command.ts` — `buildUnifiedSkillRows` (:349–383), `buildSkillRows` (:326–347), `normalizePathForKey` (:122–126), `createExternalSkillId` (:143–150), `categoryForScope` (:139–141), `collectLoadedSkillsFromCommands` (:233–267).
**Signature:** `buildUnifiedSkillRows(managedSkills: SkillIndex[], loadedSkills: LoadedSkillRow[], selectedSkillIds?: Set<string>, sortMode?: SkillSortMode) → SkillModalRow[]`.
**Data Shape:** every row carries `skillId` (store ids like `global:<name>` / `project:<project>:<name>` vs synthesized `` `external:${slug}:${sha1(name|path).slice(0,10)}` ``), `category: "G"|"P"|"E"`, `mutable: boolean` (E rows are always read-only), and a prebuilt `searchText` concatenation used by fuzzy filtering.

### Decisive source
```ts
const managedPathKeys = new Set(managedRows.map((row) => normalizePathForKey(row.path)));
const externalPathKeys = new Set<string>();
for (const loaded of loadedSkills) {
  const loadedKey = normalizePathForKey(loaded.path);
  if (managedPathKeys.has(loadedKey)) continue;      // managed wins: same file listed once as G/P
  if (externalPathKeys.has(loadedKey)) continue;     // dedupe externals among themselves
  externalPathKeys.add(loadedKey);
  ...
}
```
`normalizePathForKey` = `path.resolve` → backslash→slash → lowercase **only on win32** — so case is preserved on POSIX and collisions collapse exactly on Windows.
`collectLoadedSkillsFromCommands` keeps only commands whose `source === "skill"` AND that carry a non-empty trimmed `sourceInfo.path`; it strips the optional `skill:` prefix from names, tolerates non-record/non-string junk per entry, and returns rows sorted by displayName (:233–267).

**Flow:** (1) managed rows built straight from `SkillIndex`; (2) loaded runtime rows filtered/dedupe-checked against BOTH key sets; (3) `[...managedRows, ...externalRows]` sorted by `compareSkillRows` (:195–231): name mode = displayName.localeCompare then category order; recency modes = primary date desc (updated falls back to created via `recencyValue`) with secondary-date tiebreak, empty dates sort LAST, category order G<P<E as final tiebreak.
**Invariant:** identity across the two worlds is PATH-based, not id-based — an E row whose path equals a managed row's path is suppressed because the managed copy is mutable and authoritative. A porter who keys the dedupe on name instead of normalized path double-lists skills stored under different names in the index vs their command registration. External ids are content-addressed (`name|filePath` sha1) precisely because they have no stable store identity; they must be recomputable to survive selection sets across rebuilds.
**Probe:** `tests/handlers/skills-command.test.ts` — "buildUnifiedSkillRows merges managed and external skills" (:133), "collectLoadedSkillsFromCommands ignores malformed and pathless commands" (:116, 8-entry junk table → exactly 1 survivor), "keeps managed skills sorted by updated recency" (:144). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "buildUnifiedSkillRows normalizePathForKey createExternalSkillId collectLoadedSkillsFromCommands", limit: 5 })`

## Verdict
Adopt for any UI merging a durable store inventory with a runtime/plugin-loaded inventory of the same artifacts. Adapt the category letters and id grammar; keep the normalized-path collision rule and recompute-able synthetic ids. Omit nothing — the whole seam is ~60 lines.
