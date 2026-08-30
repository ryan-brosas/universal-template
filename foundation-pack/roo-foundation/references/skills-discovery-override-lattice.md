<!-- capsule-v2 -->
# SkillsManager discovery & override lattice — which of four skill homes wins, and what makes a skill valid?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When the same skill name exists in global `.agents`, project `.agents`, global `.roo`, and project `.roo` (plus mode-specific dirs), which one does a task see?

## Four-home scan with order-encoded priority + explicit override comparator
**Path/Symbol:** `src/services/skills/SkillsManager.ts:SkillsManager` — `discoverSkills` :43, `loadSkillMetadata` :92, `getSkillsForMode` :184, `shouldOverrideSkill` :229, `getSkillsDirectories` :567, `setupFileWatchers` :648.
**Signature:** `discoverSkills(): Promise<void>`; `getSkillsForMode(currentMode: string): SkillMetadata[]`; `createSkill(name, source, description, modeSlugs?)`; internal key `${source}:${mode || "generic"}:${name}`.
**Data Shape:** `SkillMetadata = { name, description(1–1024 chars trimmed), path, source: "global"|"project", mode?(deprecated), modeSlugs?: string[] }`; frontmatter parsed by gray-matter from each `<dir>/<name>/SKILL.md`.

### Decisive source
```ts
// Processing order (later directories override earlier ones at the same source level):
// - Global: .agents/skills first, then .roo/skills (so .roo wins)
dirs.push({ dir: path.join(globalAgentsDir, "skills"), source: "global" })
… // per-mode skills-{mode} dirs after each generic dir; project mirrors global
…
// Priority: project > global, mode-specific > generic … then keep existing (first wins)
const existingHasModes = existing.modeSlugs && existing.modeSlugs.length > 0
const newHasModes = newSkill.modeSlugs && newSkill.modeSlugs.length > 0
if (newHasModes && !existingHasModes) return true
if (!newHasModes && existingHasModes) return false
return false
```

**Flow:** clear map → scan dirs in fixed order (global .agents → project .agents → global .roo → project .roo, generic before each mode variant) → per entry: stat must be a directory (symlink-following `fs.stat`, realpath first so symlinked skills DIRS work), read SKILL.md, require frontmatter `name`+`description`, REQUIRE frontmatter name === directory/symlink entry name (spec rule), validate name format via shared `validateSkillNameShared` (64-char cap), trim+bound description. Mode resolution precedence: frontmatter `modeSlugs` array > legacy frontmatter `mode` string > directory-based `skills-{mode}`. Empty `modeSlugs: []` normalizes to undefined = "any mode". Watchers on every home's `**/SKILL.md` (created in test-skip guard) trigger FULL re-discovery.
**Invariant:** identity is DIRECTORY NAME, not frontmatter (`frontmatter.name !== effectiveSkillName` → skill silently skipped with console.error); same-key later scans REPLACE earlier ones (order encodes `.roo` over `.agents` within a source level) while cross-source conflicts resolve through shouldOverrideSkill where EQUAL specificity keeps the FIRST seen (project already scanned later, so it still wins). Delete/move operate on whole directories and re-discover afterward.
**Probe:** `grep -c "frontmatter.name !== effectiveSkillName" src/services/skills/SkillsManager.ts` → 1; `grep -c 'skills-\${mode}' src/services/skills/SkillsManager.ts` → 8 (4 homes × push+watch); `grep -c 'shouldOverrideSkill' src/services/skills/SkillsManager.ts` → 3.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "SkillsManager discoverSkills shouldOverrideSkill modeSlugs", limit: 10 });
```
(live-verified rank#1 discoverSkills :43–50, rank#2 shouldOverrideSkill :229–252).

## Verdict
Adopt the four-home lattice and directory-name identity rule wholesale — they implement an agentskills.io-compatible layout that also accepts `.claude/`-style packs. Adapt home paths to your host. Omit VS Code watcher wiring (replace with chokidar). Direct tests: `src/services/skills/__tests__/SkillsManager.spec.ts` (describe :115; discovery its incl. symlinked dir :509 / symlinked subdir :566 / ".roo prioritized over .agents with same name" :720; getSkillsForMode describe :830).
