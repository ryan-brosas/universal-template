<!-- capsule-v2 -->
# Per-repo worktree config store — where do per-repository preferences live so they survive folder renames, stay shared across linked worktrees, and never corrupt on a bad edit?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you persist per-repo settings (setup script, launcher commands, default base ref) keyed by something stable when the on-disk project folder name can change under you?

## Repo-id-keyed versioned JSON with fail-open defaults
**Path/Symbol:** `packages/server/src/worktree-config-store.ts:WorktreeConfigStore` (:65–131), `DEFAULT_CONFIG` (:26–31), `sanitizeSetupScript` (:33–34), `sanitizeOpenInCommands` (:38–50), `worktreeConfigPathFor` (:135–136); schema `packages/server/src/schemas.ts:worktreeRepoConfigFileSchema` (:907–914); key source `repoId` (`git-worktrees.ts`:47–48).
**Signature:** `get(cwd): Promise<WorktreeRepoConfig>`; `update(cwd, patch: Partial<WorktreeRepoConfig>): Promise<WorktreeRepoConfig>` (merge-into-prior semantics).
**Data Shape:** Stored file `~/.localterm/worktree-configs/<sha256(mainRoot)[:12]>.json`, strict zod v1 `{version:1, setupScript ≤8192, openInCommands ≤20×{id,label,command}, baseRef:"fresh"|"head"}`; wire shape drops the version tag. All defaults empty/off so upgrading is a no-op until configured.

### Decisive source
```ts
private async readStored(cwd: string): Promise<StoredWorktreeRepoConfig> {
  const mainRoot = await mainWorktreeRoot(cwd);
  if (!mainRoot) return { ...DEFAULT_CONFIG };
  const filePath = this.configPathFor(repoId(mainRoot));
  let raw: string;
  try {
    raw = fs.readFileSync(filePath, "utf8");
  } catch {
    return { ...DEFAULT_CONFIG };
  }
  let json: unknown;
  try {
    json = JSON.parse(raw);
  } catch {
    return { ...DEFAULT_CONFIG };
  }
  const parsed = worktreeRepoConfigFileSchema.safeParse(json);
  if (!parsed.success) return { ...DEFAULT_CONFIG };
  ...
}
```
Sanitize-on-write with client-stable ids:
```ts
const seen = new Map<string, WorktreeOpenInCommand>();
for (const raw of commands ?? []) {
  const id = raw.id.slice(0, MAX_WORKTREE_OPEN_IN_ID_LENGTH).trim();
  const label = raw.label.trim().slice(0, MAX_WORKTREE_OPEN_IN_LABEL_LENGTH);
  const command = raw.command.trim().slice(0, MAX_WORKTREE_OPEN_IN_COMMAND_LENGTH);
  if (!id || !label || !command) continue;
  seen.set(id, { id, label, command });   // dedupe by id, last wins
}
return [...seen.values()].slice(0, MAX_WORKTREE_OPEN_IN_COMMANDS);
```

**Flow:** every read/write re-resolves mainRoot → repoId hash → path under the state dir (NOT the repo) → read anomalies of ANY kind (missing root, unreadable, unparsable, schema mismatch) collapse to defaults rather than throwing → update merges patch fields over current, sanitizes, persists via mkdir+tmp+rename → route PUT `/api/git/worktrees/config` returns the merged config; POST `/git/worktrees` reads it for the default baseRef and returns `setupCommand` for the new tab's initial command.
**Invariant:** The key is a hash of the MAIN worktree's absolute path, so the config survives auto-folder renames and is shared by every linked worktree by construction. A corrupt file must degrade to defaults (a broken preference file must never take the daemon down). Sanitization happens on WRITE so the stored file is always canonical, and once more on load for files written by older versions.
**Probe:** `packages/server/tests/worktree-config-store.test.ts` — defaults with no saved config :42–58; persist/reload/merge :60–93 (uses exported `worktreeConfigPathFor` + `mainWorktreeRoot` to compute the expected path; second update preserves earlier fields); sanitize open-in (empty label dropped, dup id last-wins) :95–117. Executed this pass: 3/3 green.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "worktree config store sweep", limit: 10 });
```
Executed live pre-write: rank rows cover `WorktreeConfigStore.constructor/get/update/persist/readStored`, `toWire` :52–56, `sanitizeOpenInCommands` :38–50, `sanitizeSetupScript` :33–34, `worktreeConfigPathFor` :135–136 — line-exact vs disk.

## Verdict
Adopt: identity-hash keying outside the mutable namespace, three-layer read fallback (fs→JSON→zod each failing open to defaults), merge-patch update with write-time sanitization and client-stable row ids; adapt the field set and caps; omit the version literal only if you have no migration story yet (then add one before the first format change — see store-migration-ladder capsule for the ladder pattern this store intentionally doesn't need at v1). Trap: keying by folder NAME — same-named repos from different paths would share settings (the repo-id exists precisely to prevent that).
