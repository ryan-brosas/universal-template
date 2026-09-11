<!-- capsule-v2 -->
# Symlink skill installer — how do you install agent skills canonically once and expose them to multiple CLAs through symlinks without ever clobbering user data?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** How do you ship bundled SKILL.md assets that work both from a package tree and a compiled single binary, install them idempotently into one canonical dir, and safely mirror them via symlinks for consumers that only read their own directory?

## Connected graph-selected seam
**Path/Symbol:** `src/commands/skills.ts` — `getSkillContent` (:62–75) dual distribution resolver, `installSkill` (:106–133), `uninstallSkill` (:140–168), `listSkills` (:179–211), `ensureSymlink` (:217–252); layout: canonical `~/.agents/skills/<name>/SKILL.md`, mirror symlink `~/.claude/skills/<name>` ("Claude Code follows symlinks"; pi + Codex read the agents dir globally).
**Signature:** `ensureSymlink(linkPath: string, targetDir: string): Promise<void>`; `installSkill(name, model?): Promise<InstallResult>` with `status: 'installed'|'updated'|'unchanged'`.
**Data Shape:** embedded assets via `import x from '<path>.md' with { type: 'file' }` (baked into `bun build --compile` binaries, resolved on disk otherwise); skills carry `name:` frontmatter used as the health marker.

### Decisive source
```ts
async function ensureSymlink(linkPath: string, targetDir: string): Promise<void> {
  const absTarget = resolve(targetDir);
  try {
    const stat = await lstat(linkPath);
    if (stat.isSymbolicLink()) {
      const current = resolve(dirname(linkPath), await readlink(linkPath));
      if (current === absTarget) return;            // already correct
      await rm(linkPath, { force: true });          // points elsewhere → replace
    } else if (stat.isDirectory()) {
      const entries = await readdir(linkPath).catch(() => []);
      if (entries.length === 0) await rm(linkPath, { recursive: true, force: true });
      else throw new Error(`Refusing to overwrite non-empty directory at ${linkPath}. …`);
    } else {
      await rm(linkPath, { force: true });          // stray file → replace
    }
  } catch (e) { if (e.code !== 'ENOENT') throw e; }
  await mkdir(dirname(linkPath), { recursive: true });
  await symlink(absTarget, linkPath, 'dir');
}
```

**Flow:** resolve content (disk-first, embedded fallback — one resolver for both distribution shapes) → render `{{model}}` placeholders → write canonical file only when content differs (status tri-state installed/updated/unchanged) → ensureSymlink the consumer path; uninstall deletes canonical unconditionally but removes the link **only if lstat says symlink AND readlink resolves to our canonical dir**; list reports `installed` (frontmatter `name:` line matches) and `symlinkOk` (linked SKILL.md reachable).
**Invariant:** never clobber user-owned data — a real non-empty directory at the link path aborts loudly rather than being replaced, and uninstall preserves it (test-pinned); re-running install converges to exactly one canonical copy + one symlink; ENOENT is the expected "nothing there yet" case, every other inspect error propagates.
**Probe:** `bun test tests/commands/skills.test.ts` executed live at pin: **10 pass / 0 fail / 58 expect()** — includes idempotent reinstall (`unchanged`), stale-content update, missing-skill uninstall no-op, and "uninstall does NOT clobber a user-owned real directory"; `tests/commands/init-skills.test.ts` 1 pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "installSkill ensureSymlink uninstallSkill listSkills getSkillContent embedded asset", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: canonical-dir + per-consumer-symlink topology, content-compare tri-state installs, the five-arm ensureSymlink ladder (correct / wrong-target / empty-dir / non-empty-dir-refusal / file), and readlink-verified unlinking. Adapt target directories (`~/.agents`, `~/.claude`) and the embedded-asset mechanism (`with { type: 'file' }` is Bun-specific — use your bundler's asset imports). Omit the veda onboarding-doc sync step.
