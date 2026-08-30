<!-- capsule-v2 -->
# Skill migration sentinel — warnings delta-latch lets shadow-blocked skills retry without wedging startup

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** A one-time migration must not rerun forever, but a permanently-shadowed legacy skill (blocked by the host's own file) would emit its warning on EVERY startup — how do you latch completion without treating foreign blockers as migration failures?

## Migration sentinel
**Path/Symbol:** `src/store/skill-store.ts` — `migrateLegacySkills` (:208–231), flat-markdown normalization :277–321, legacy-dir migration :233–275, sentinel path `<agentRoot>/pi-hermes-memory/.skills-migrated-to-extension-storage` (:171–172); direct tests `tests/store/skill-store.test.ts:504–620`.
**Signature:** `migrateLegacySkills(): Promise<{ migrated: number; skipped: number; warnings: string[] }>`.
**Data Shape:** sentinel file contains an ISO timestamp line; existence = migration done.

### Decisive source
```ts
// migrateLegacySkills (208-231): TWO phases with different idempotence rules
await this.migrateFlatMarkdownInGlobalSkillsDir(result);   // runs ALWAYS, even post-sentinel
if (await exists(this.migrationSentinelPath)) return result; // phase-2 gated by sentinel

await fs.mkdir(path.dirname(this.migrationSentinelPath), { recursive: true });
const warningsBefore = result.warnings.length;
try {
  await this.migrateLegacyMarkdownSkills(result);
} finally {
  // Only THIS migration's own warnings may hold back its sentinel:
  if (result.warnings.length === warningsBefore) {
    await fs.writeFile(this.migrationSentinelPath, `${new Date().toISOString()}\n`, "utf-8");
  }
}

// Flat-markdown normalization (:277-321) — self-healing, always-on:
// <globalSkillsDir>/<file>.md → <slug>/SKILL.md via atomicWrite, then fs.rm(legacyPath).
// If <slug>/SKILL.md already exists → the flat file is STALE: rm it, count skipped.
// Legacy memory/skills/*.md migration (:233-275) — same shape but NO source deletion,
// and target-exists counts as skipped WITHOUT deleting (never overwrite user state).

// migrateFlatMarkdown / migrateLegacy per-file catch pushes into result.warnings
```

**Flow:** (1) Phase 1 (flat-markdown normalization under the CURRENT global root) runs on every startup regardless of sentinel — it is idempotent by construction and self-heals stale leftovers. (2) Phase 2 (legacy `memory/skills/` import) is one-shot, gated by the sentinel file. (3) The sentinel is written in a `finally` ONLY when this run produced zero NEW warnings compared to the pre-phase-2 count — so warnings from phase 1 (e.g. a skill permanently shadowed in Pi's own root, reported every time) do NOT hold back the latch, while genuine phase-2 failures (unreadable files, write errors) DO prevent latching, making the whole phase-2 retry next startup. (4) Per-file errors are caught and pushed as warnings — one bad file never aborts the batch.

**Invariant:** the latch measures only the DELTA of warnings attributable to phase 2 (`warnings.length === warningsBefore`), which decouples "migration incomplete" from "environment has a permanent conflict" — the comment names this exactly: *"Only this migration's own warnings may hold back its sentinel — a permanently shadowed skill reported above must not make it retry forever."* Migration never overwrites existing targets (skips instead); flat-normalization DELETES the flat source after successful folder creation but the legacy dir keeps originals.

**Probe:** `tests/store/skill-store.test.ts` — `migrates legacy memory/skills/*.md files into global Pi skills` (:505), `does not rerun after the sentinel is created` (:531), `does not overwrite an existing global skill unexpectedly` (:549), `migrates flat markdown files under global skills root into SKILL.md folders` (:578), `does not write the sentinel when warnings occur, so migration can retry` (:596). Coverage caveat: `tests/` is excluded from the graph index by design; probes are source-grounded from on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "migrateLegacySkills sentinel warnings retry", limit: 5 });
// live-verified rank-1: SkillStore.migrateLegacySkills :208-231
```

## Verdict
Adopt the two-tier migration split (always-idempotent normalization + sentinel-gated one-shot import) and the warnings-delta latch whenever some migration warnings are permanent-by-design. Adapt sentinel location/format. Omit the flat-source deletion if your target cannot afford any data loss during normalization.
