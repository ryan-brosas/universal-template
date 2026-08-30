<!-- capsule-v2 -->
# Skill store — procedural memory as Pi-native skills with duplicate/similar/shadow guards

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent persist procedural memory as versioned skill files (global + project scopes) — creating/patching/editing/moving/deleting with duplicate, similar, name-collision, and shadow guards, section-aware patching, and legacy migration — without ever writing a skill Pi would silently shadow?

## SkillStore
**Path/Symbol:** `src/store/skill-store.ts:SkillStore` (class, 156–950); `create` (365–461), `patch` (463–524), `edit` (526–560), `move` (562–697), `delete` (699–716), `loadIndex` (342–357), `migrateLegacySkills` (208–231), `normalizeSkillPatchContent` (91–153). Helpers in `src/store/skill-utils.ts` — `slugify` (61–68), `parseFrontmatter` (22–37), `formatFrontmatter` (43–59), `buildSkillId`/`parseSkillId` (103–124), `jaccardSimilarity` (89–101), `tokenizeForSimilarity` (80–87).
**Signature:** `new SkillStore({globalSkillsDir?, piGlobalSkillsDir?, projectSkillsDir?, projectName?, legacySkillsDir?, migrationSentinelPath?})`; `create(name, description, body, scope?) → SkillResult`; `patch(skillId, section, newContent) → SkillResult`.
**Data Shape:** global skills at `<globalSkillsDir>/<slug>/SKILL.md`; project skills at `<projectSkillsDir>/<slug>/SKILL.md`. `SkillResult = { success, message?, fileName?, skillId?, scope?, path?, conflictType?, similarSkillIds?, suggestedAction? }`. `skillId` = `global:<slug>` or `project:<projectName>:<slug>`. Frontmatter: `name`, `description`, `version`, `created`, `updated`, optional `display_name`.

### Decisive source
```ts
// create (365-461): guards run in order — duplicate, similar, name-collision, shadow
const slug = slugify(name);
const existing = await this.findLocationById(skillId);
if (existing) return { success:false, error:`Skill '${slug}' already exists...`, conflictType:"duplicate", suggestedAction:"patch" };
if (resolvedScope === "global") {
  const similar = await this.findSimilarGlobalSkillIds(slug, description); // jaccard over tokens
  if (similar.length > 0) return { ..., conflictType:"similar", suggestedAction:"patch" };
  const colliding = await this.findNameCollisionGlobalSkillIds(slug, description);
  if (colliding.length > 0) return { ..., conflictType:"name-collision", suggestedAction:"rename" };
  const shadowedBy = await this.findShadowingPiGlobalSkill(slug); // Pi's own root loads first
  if (shadowedBy) return { ..., conflictType:"name-collision", suggestedAction:"rename", error:`Pi already loads a global skill named '${slug}' from ${shadowedBy}...` };
}
await this.atomicWrite(filePath, formatFrontmatter({ name: slug, displayName: name, description, version: 1, created: stamp, updated: stamp, body }));

// normalizeSkillPatchContent (91-153): coerce JSON string arrays, reject objects/headers
if (looksLikeJsonArray(content)) {
  const items = parsed.filter(i => typeof i === "string").map(i => i.trim()).filter(Boolean);
  if (key === "when to use") content = items.join("\n\n");
  else if (LIST_SECTIONS.has(key)) content = formatPatchList(sectionName, items); // procedure/verification → ordered, pitfalls → bullets
  else content = items.map(i => `- ${i}`).join("\n");
}
if (/^#{1,6}\s+\S/m.test(content)) return { error: "Patch content must not include Markdown section headers..." };

// patch (463-524): replace the exact ## section body, preserving other sections
for (let i = 0; i < lines.length; i++) {
  if (isExactSectionHeader(lines[i], sectionName)) {
    result.push(sectionHeader);
    for (const bodyLine of content.split("\n")) result.push(bodyLine);
    found = true; i++;
    while (i < lines.length && !lines[i].trim().startsWith("## ")) i++;
    if (i < lines.length) result.push(lines[i]);
  } else result.push(lines[i]);
}
```

**Flow:** (1) `create` slugifies, runs the guard chain (duplicate → similar → name-collision → Pi-shadow), then writes `SKILL.md` with frontmatter. (2) `patch` normalizes the section content (coercing JSON arrays, rejecting objects/header-injection), then replaces the exact `## <section>` body while preserving all other sections, bumping `version`. (3) `edit` replaces description/body. (4) `move` renames within the same filesystem, falling back to copy+remove across devices with rollback. (5) `migrateLegacySkills` normalizes flat markdown and migrates legacy `memory/skills/*.md` into `<slug>/SKILL.md` folders, writing a sentinel only when there are no warnings. (6) `loadIndex` sorts by updated desc, created desc, scope, name.

**Invariant:** a skill is never created that Pi would silently shadow (Pi's own global root loads first); a similar skill is enhanced via patch rather than duplicated; patch never wipes or splices unrelated sections; version increments on every mutation; the migration sentinel is only written when migration fully succeeds.

**Probe:** `tests/store/skill-store.test.ts` — `writes global skills to <slug>/SKILL.md` (:73), `returns error for duplicate slug in same scope` (:143), `blocks creating a similar global skill and suggests patching` (:155), `blocks near-name global collisions even when descriptions diverge` (:179), `replaces an existing section by skill id` (:329), `coerces JSON string arrays into ordered Procedure steps` (:355), `rejects JSON object patch payloads` (:372), `rejects patch content that injects section headers` (:395), `refuses a global name Pi already loads instead of writing a shadowed copy` (:631), `migrates legacy memory/skills/*.md files into global Pi skills` (:505). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "SkillStore create patch move migrateLegacySkills normalizeSkillPatchContent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the slugify + frontmatter skill format, the guard chain (duplicate/similar/name-collision/shadow), the section-aware patch with JSON-array coercion, the version bumping, and the legacy migration sentinel. Adapt the skill directory layout, the similarity threshold, and the frontmatter fields to the host. Omit the Pi-shadow detection and the cross-scope move unless a target has a host skill system with its own load precedence.
