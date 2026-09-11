<!-- capsule-v2 -->
# Workspace config store — cwd/.pi config JSON with load/save cwd asymmetry and merge-preserving writes

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How should an extension persist small workspace-scoped settings without clobbering other keys in the same file?

## Load reads process.cwd(); save takes explicit cwd
**Path/Symbol:** `src/global-config.ts:24-38` (`loadGlobalModel`), :45-65 (`saveGlobalModel`).
**Signature:** `loadGlobalModel(): {provider, modelId} | null` (path from `process.cwd()`); `saveGlobalModel(cwd: string, model): string` (returns written path).
**Data Shape:** File `<cwd>/.pi/supervisor-config.json`; shape `{ model?: { provider, modelId } }` plus arbitrary sibling keys preserved on save.

### Decisive source
```ts
export function loadGlobalModel(): { provider: string; modelId: string } | null {
  const configPath = join(process.cwd(), CONFIG_DIR, CONFIG_FILE);
  ...
}
export function saveGlobalModel(cwd: string, model: { provider: string; modelId: string }): string {
  const dir = join(cwd, CONFIG_DIR);
  const configPath = join(dir, CONFIG_FILE);
  let existing: SupervisorConfig = {};
  if (existsSync(configPath)) {
    try { existing = JSON.parse(readFileSync(configPath, 'utf-8')) as SupervisorConfig; }
    catch { /* ignore parse errors — start fresh */ }
  }
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  const merged: SupervisorConfig = { ...existing, model };
  writeFileSync(configPath, JSON.stringify(merged, null, 2) + '\n', 'utf-8');
  return configPath;
}
```

**Flow:** load ⇒ missing file or parse error or missing fields ⇒ null (defaults cascade to session model at call sites) → save ⇒ read-modify-MERGE (spread existing, overwrite only the `model` key) → ensure dir → pretty-write with trailing newline.
**Invariant:** The cwd asymmetry is real and deliberate: load uses `process.cwd()` (no arg), save uses the passed `ctx.cwd` — a porter unifying them must decide which semantics survive (callers pass ctx.cwd so saves follow the SESSION's workspace even under daemon cwd drift). Corrupt JSON never throws: load returns null, save starts fresh but still merges nothing.
**Probe:** `grep -c "SUPERVISOR.md" src/core/prompt-loader.ts` → 4 (sibling .pi convention); `grep -c "CONFIG_DIR = '.pi'" src/global-config.ts src/core/prompt-loader.ts` → 1 + 1. Direct tests: `tests/global-config.test.ts:7` describe('global-config').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "loadSystemPrompt SUPERVISOR.md project global built-in", limit: 10 });
```
(Adjacent seam — same `.pi` discovery family; for this capsule's symbols use name_pattern `loadGlobalModel|saveGlobalModel`.)

## Verdict
Adopt merge-preserving single-key writes for shared config files. Resolve the load-cwd question explicitly for your host rather than copying the asymmetry blindly. Omit the trailing-newline/pretty-print cosmetics at your repo's hygiene peril.
