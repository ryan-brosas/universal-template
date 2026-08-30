<!-- capsule-v2 -->
# Cross-scope skill move — atomic rename with EXDEV copy fallback and duplicate-proof rollback

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** How do you move a file-backed record between two storage scopes (e.g. global→project) so it can never exist in BOTH scopes, including when the scopes sit on different filesystems?

## Skill move
**Path/Symbol:** `src/store/skill-store.ts` — `SkillStore.move` (:562–697), same-fs rename :623–650, EXDEV fallback + rollback :652–697, `removeEmptyParents` (:935–949), `atomicWrite` (:922–933); direct tests `tests/store/skill-store.test.ts:429–503`.
**Signature:** `move(skillId: string, targetScope: SkillScope): Promise<SkillResult>`.
**Data Shape:** success carries the NEW skillId/path/scope; failures carry `conflictType: "scope-conflict" | "similar" | "name-collision"` with `suggestedAction`.

### Decisive source
```ts
// Pre-gates (:563-621): load → parse id → same-scope is a SUCCESS no-op ("already global/project")
// → target root must exist (project needs active project) → destination slug must be FREE
//   (conflictType:"scope-conflict") → moving INTO global re-runs similarity + name-collision gates.
// Same-filesystem fast path (:625-650): rename FIRST for atomicity, no duplicate window:
try {
  await fs.rename(doc.path, targetPath);
  if (path.basename(doc.path) === "SKILL.md")
    await this.removeEmptyParents(path.dirname(doc.path), this.getScopeRoot(doc.scope));
  return { success: true, ..., skillId: targetSkillId, scope: targetScope, path: targetPath };
} catch (renameError) {
  const code = renameError?.code;
  if (code !== "EXDEV") return { success: false, error: `Move to ${targetScope} failed before copy...` };
}
// Cross-device fallback (:652-687): copy (atomicWrite) then remove source;
// if source unlink FAILS → best-effort rollback removes the destination copy,
// so duplicates across scopes cannot silently persist:
try {
  await fs.unlink(doc.path);
  ...removeEmptyParents...
} catch (error) {
  let rollbackFailed = false;
  try { await fs.unlink(targetPath); ... } catch { rollbackFailed = true; }
  return { success: false, error: rollbackFailed
    ? `Move to ${targetScope} failed while removing source skill '${skillId}', and rollback also failed...`
    : `Move to ${targetScope} failed while removing source skill '${skillId}'. Rolled back destination copy...` };
}

// removeEmptyParents (935-949): walk up deleting EMPTY dirs, stop at scope root; any error stops silently
while (current.startsWith(stopDir) && current !== stopDir) {
  const entries = await fs.readdir(current);
  if (entries.length > 0) return;
  await fs.rmdir(current); current = path.dirname(current);
}
```

**Flow:** (1) Identity pre-gates run BEFORE any filesystem mutation: unknown id, invalid id, already-in-scope (reported as SUCCESS with unchanged state), missing project root, occupied destination slug, and (for moves into global) the same similar/name-collision gates as create — a moved skill can't become a global duplicate either. (2) Same device: single `fs.rename`, no window where both copies exist; empty parent `<slug>/` dirs are pruned upward but never past the scope root. (3) EXDEV (cross-device): atomic temp+rename COPY to destination, then source unlink; if unlink fails, the destination copy is REMOVED (best-effort rollback) and the error states which of the two cleanup outcomes happened — only a double failure can leave a duplicate, and that state is named loudly in the error text.

**Invariant:** at most one live copy exists across scopes in every terminating state except the explicitly-named rollback-also-failed case. Non-EXDEV rename errors fail BEFORE copy ("failed before copy"), never leaving half-states. The rollback error messages distinguish rolled-back vs rollback-failed so callers can report accurately. Empty-directory pruning is bounded by the scope root (`startsWith(stopDir)` guard prevents escaping into shared ancestors).

**Probe:** `tests/store/skill-store.test.ts` — `moves a global skill into the active project scope` (:430), `moves a project skill into global scope` (:441), `blocks move when destination scope already has the same slug` (:452), `returns an error when moving to project scope without an active project` (:468). Coverage caveat: `tests/` is excluded from the graph index by design; probes are source-grounded from on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "SkillStore move cross-device rename fallback", limit: 5 });
// live-verified rank-1: SkillStore.move :562-697 (rank-2 = tests/handlers/skills-command.test.ts move)
```

## Verdict
Adopt the ordering (identity gates → atomic rename-first → EXDEV copy+unlink with destination-removing rollback) for any scoped record store backed by files. Adapt gate sets and path shapes. Omit the empty-parent pruning unless your layout creates per-record directories.
