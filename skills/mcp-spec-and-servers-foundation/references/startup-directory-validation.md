<!-- capsule-v2 -->
# Startup directory validation — how must an allowlist server behave at boot when SOME (or all) of its configured directories are inaccessible or not directories?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** What is the fail-partial vs fail-all boundary for startup path arguments, and what exact stderr contract do the spawn tests pin?

## Per-item isolation: warn-and-skip bad dirs; exit(1) ONLY when nothing usable remains
**Path/Symbol:** `src/filesystem/index.ts` argv validation (startup block) + direct test `src/filesystem/__tests__/startup-validation.test.ts` (whole file, 100L: `spawnServer(args, timeoutMs)` harness :12–37; four behavior cases :56–99). Complements `roots-validation-ladder.md` (per-REQUEST Root.uri validation) and `filesystem-sandbox.md` (per-operation containment).

**Signature:** `node dist/index.js <dir...>` → per-dir check: stat-accessible? is-directory? → collect warnings on stderr → start if ≥1 valid; else print `Error: None of the specified directories are accessible` and `process.exit(1)`.

**Data Shape:** success banner pinned verbatim: `Secure MCP Filesystem Server running on stdio`; warning prefix: `Warning: Cannot access directory <path>`; non-directory variant: `Warning:` + `not a directory`.

### Decisive source
```ts
// __tests__/startup-validation.test.ts:63-85 — partial failure tolerates, total failure exits
it('should skip inaccessible directory and continue with accessible one', async () => {
  const result = await spawnServer([nonExistentDir, accessibleDir]);
  expect(result.stderr).toContain('Warning: Cannot access directory');
  expect(result.stderr).toContain(nonExistentDir);
  expect(result.stderr).toContain('Secure MCP Filesystem Server running on stdio'); // still boots
});
it('should exit with error when ALL directories are inaccessible', async () => {
  const result = await spawnServer([nonExistent1, nonExistent2]);
  expect(result.exitCode).toBe(1);
  expect(result.stderr).toContain('Error: None of the specified directories are accessible');
});
```

**Flow:** spawn with args → each dir validated independently (missing dir ⇒ warn+skip :63–74; a FILE path ⇒ "not a directory" warn, continue :87–99) → all-valid ⇒ banner, no errors (:56–61) → zero-valid ⇒ error line to stderr, exit code 1, no banner. The harness kills via SIGTERM after a timeout and treats "still running" as success (exitCode null).

**Invariants:**
1. **One bad path never blocks the others** — failing closed on ANY invalid arg would let a typo take down a working sandbox config.
2. **Fail-closed only at zero**: no accessible directory ⇒ refuse to serve (a server that starts with an EMPTY allowlist would silently expose nothing or, worse, get misconfigured later into exposing everything).
3. **Diagnostics go to stderr with greppable prefixes** (`Warning:` / `Error:` / fixed banner) — the stdout channel stays protocol-pure (stdio purity invariant).
4. Non-directory files are warned distinctly from missing paths — operators can tell typos from wrong-type args.

**Probe:** `__tests__/startup-validation.test.ts` IS the probe (spawn-level, real process). Coverage caveat: permission-denied (EACCES) variants untested; symlinked dirs untested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "startup directory validation accessible exit 1 warning stdio", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt warn-and-skip with fail-closed-at-empty for any allowlist-driven server boot; adapt banner/warning wording to your ops tooling (keep them on stderr); omit nothing — the exit-code boundary is the security-relevant part. Sits upstream of `filesystem-sandbox.md`: this gates WHICH roots exist before that capsule governs WHAT paths resolve inside them.
