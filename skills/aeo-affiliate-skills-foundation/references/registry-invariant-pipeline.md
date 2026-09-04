<!-- capsule-v2 -->
# Registry invariant pipeline — how does a markdown skill corpus stay in verified sync with registry.json?

**Source:** aeo-affiliate-skills MIT `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory `aeo-affiliate-skills`. **Question:** When registry.json is generated from a tree of SKILL.md files, which invariants must hold between generator, corpus, and committed artifact — and who enforces them?

## Stage-ordered generator + zero-dep invariant suite coupled by CI
**Path/Symbol:** `scripts/generate-registry.js`:`main` (66–113), `parseFrontmatter` (25–40), `parseOpenaiYaml` (42–51), `detectToolsFromBody` (53–64); enforcement `tests/test-registry-invariants.ts` (whole file; `getSkillFiles` :17–35, name assertion :55).
**Signature:** `function main(): void` (writes `registry.json`, pretty-printed + trailing newline); `function parseFrontmatter(content): Record<string,string>`; `function getSkillFiles(): Array<{stage, slug, path}>`.
**Data Shape:** Fixed `STAGES` map: 8 stage keys → `{label, description, order}`. Registry entry: `{name, slug, stage, version: "1.0.0", description, path, agent_compatible: true, tools[], author}`. Registry root: `{version, generated_at, stages, skills}`. Frontmatter parser handles only `key: value` lines plus indented continuations folded with spaces.

### Decisive source
```js
const stageDirs = fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter(d => d.isDirectory() && STAGES[d.name])          // unlisted stages silently dropped
  .sort((a, b) => STAGES[a.name].order - STAGES[b.name].order);
...
// Merge: openai.yaml tools take precedence, body detection fills gaps
const mergedTools = [...new Set([...(openai.tools || []), ...bodyTools])].sort();
skills.push({
  name: fm.name || skillDir.name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  ...
```

…versus the test that constrains that fallback:

```ts
assert(`${file.path} name matches folder slug`,
  entry.name === file.slug, `registry=${entry.name}`);
```

and its wider sweep:

```ts
// Test 1: count parity; Test 2: every file present with matching stage/slug/name;
// Test 3: every entry's path has a SKILL.md on disk;
// Test 4: every SKILL.md starts with frontmatter ("---\n" or "---\r\n");
// Test 5: every observed stage exists in registry.stages.
if (process.exitCode) { console.error("\n❌ Registry invariants failed"); process.exit(process.exitCode); }
```

**Flow:** generator walks stage dirs filtered BY the STAGES map in `order` sequence, then skill dirs alphabetically, skipping any dir without SKILL.md; builds entries from hand-parsed frontmatter, optional `agents/openai.yaml` tool list (regex-extracted), and body-detected tool names from the fixed set {web_search, web_fetch, web_browse}; writes registry.json. The invariant test walks WITHOUT the STAGES filter (any `skills/*/*/SKILL.md` counts), so adding an unlisted stage fails count parity AND stage-map membership — the corpus cannot silently drift out of the registry. CI (`ci.yml`) runs it via `bun run test:registry`; `update-registry.yml` regenerates on `skills/**` pushes and commits only when `git diff --quiet registry.json` reports changes.
**Invariant:** The de-facto contract `entry.name === folder slug`: the generator prefers frontmatter `name:`, but the test demands equality with the directory slug, so a "pretty" frontmatter name breaks CI. Treat generator+test as one coupled unit. Also: `generated_at: new Date().toISOString()` makes output byte-nondeterministic — acceptable ONLY because consumers gate on diff-presence, not content equality.
**Probe:** Repository-owned runner executed at pin: `bun run tests/test-registry-invariants.ts` → all five tests ✅ (see verification.md P1). Source pins: `grep -n "STAGES\[d.name\]" scripts/generate-registry.js` → :70; `grep -n "name matches folder slug" tests/test-registry-invariants.ts` → :55.
**Coverage caveat:** none — both files checked `no_recorded_issue` at generation 2026-08-25T08:24:56Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aeo-affiliate-skills", query: "parseFrontmatter detectToolsFromBody registry skills", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pairing itself: a deterministic-order generator whose output is guarded by a separate zero-dependency invariant suite that re-walks the corpus with FEWER filters than the generator, run in CI, plus a bot workflow that commits regeneration only when bytes change. Adapt the frontmatter parser to your needs (this subset deliberately avoids a YAML dependency but folds continuations naively — quoted multi-line descriptions survive only as joined strings). Omit nothing silently: if you add stage filtering to your walker, mirror it in the test or you lose the drift guarantee.
