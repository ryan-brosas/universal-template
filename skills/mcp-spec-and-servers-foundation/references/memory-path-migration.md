<!-- capsule-v2 -->
# Memory-file path resolution & JSON→JSONL migration — how does a server pick its data file across env overrides, platform path shapes, and a legacy-format rename?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** Which precedence and migration rules must a storage-path resolver follow so upgrades never lose or fork user data?

## env override (abs or rel) → default; one-way json→jsonl migration only when the new file is absent
**Path/Symbol:** `src/memory/index.ts` `ensureMemoryFilePath` + `defaultMemoryPath` (exported symbols); direct test `src/memory/__tests__/file-path.test.ts` (whole file, 156L: env save/restore :12–40; absolute/relative/windows cases :42–75; migration trio :77–144).

**Signature:** `await ensureMemoryFilePath(): Promise<string>`; `defaultMemoryPath` ends with `memory.jsonl`, absolute.

**Data Shape:** decision table pinned by test:
| MEMORY_FILE_PATH | old `memory.json` | new `memory.jsonl` | result |
|---|---|---|---|
| absolute | – | – | returned AS-IS |
| relative | – | – | converted to ABSOLUTE |
| unset | exists | absent | MIGRATE content to .jsonl, delete .json |
| unset | exists | exists | use .jsonl, NO touch of .json |
| unset | absent | absent | defaultMemoryPath |

### Decisive source
```ts
// __tests__/file-path.test.ts:84-110 — migrate ONLY old-present+new-absent, verify content survives
it('should migrate from memory.json to memory.jsonl when only old file exists', async () => {
  await fs.writeFile(oldMemoryPath, '{"test":"data"}');
  ...
  expect(newFileExists).toBe(true);
  expect(oldFileExists).toBe(false);   // old file REMOVED after migration
  expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringContaining('DETECTED: Found legacy memory.json file'));
  expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringContaining('COMPLETED: Successfully migrated'));
});
it('should use new file when both old and new files exist', async () => { ... /* no migration, no console noise */ });
```
Windows case (:62–74): a `C:\temp\...` value passes through untouched on win32 but is treated as RELATIVE on POSIX — the platform split is asserted, not assumed.

**Flow:** read env → set ⇒ normalize (absolute passthrough / resolve relative) → unset ⇒ check new file first, then legacy migration (copy content verbatim, log DETECTED/COMPLETED to stderr, remove old), else default → return the resolved path. Migration preserves byte-exact content (`expect(migratedContent).toBe(testContent)` :136–144).

**Invariants:**
1. **Migration is one-way and guarded**: it runs ONLY when the legacy file exists AND the target doesn't — re-running with both present must never clobber newer .jsonl data with stale .json data.
2. **Relative env values are resolved against a deterministic base**, not the process CWD at call time (test asserts absoluteness, not location).
3. **Env restore hygiene in tests** mirrors prod safety: save/delete/restore around every case.
4. Content moves VERBATIM — no reformatting during format migration.

**Probe:** `src/memory/__tests__/file-path.test.ts` IS the probe (5 behavior pins above). Coverage caveat: symlinked paths and permission-denied defaults untested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "ensureMemoryFilePath defaultMemoryPath MEMORY_FILE_PATH migration jsonl", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the decision table (new-file-wins, guarded one-way migration, verbatim copy) for any server that renamed its store format; adapt the default location and env var name; omit the demo logging strings. Complements `knowledge-graph-memory.md`, which owns the JSONL entity/relation semantics this path layer feeds.
