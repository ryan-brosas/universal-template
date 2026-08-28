<!-- capsule-v2 -->
# Bootstrap asset embedding — how do you ship bridge assets into a sandbox so snapshots survive resume cycles?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory MCP NOT connected this session → direct source+test read fallback per AGENTS.md. **Question:** a harness must install its bridge (and sometimes a CLI) into a sandbox that may be fresh, snapshot-restored, or resumed — how do you embed, place, and memoize those assets so the install is cheap and persistent?

## Cached singleton + two-candidate asset resolution + persistent placement
**Path/Symbol:** `packages/harness-claude-code/src/claude-code-bootstrap.ts` (69L whole), `packages/harness-codex/src/codex-bootstrap.ts` (60L whole), `packages/harness-opencode/src/opencode-bootstrap.ts` (58L whole), `packages/harness-deepagents/src/deepagents-bootstrap.ts` (87L whole); interface `packages/harness/src/v1/harness-v1-bootstrap.ts` (47L whole), `HarnessV1.getBootstrap` (harness-v1.ts :84–88); wiring sites claude-code-harness.ts :821, codex-harness.ts :198, opencode-harness.ts :242, deepagents-harness.ts :208.
**Signature:** `get<Name>Bootstrap(): Promise<HarnessV1Bootstrap>`; `HarnessV1Bootstrap = { harnessId, bootstrapDir, files: [{path, content}], commands: [{command}] }`.
**Data Shape:** assets are the bridge's own build artifacts read as TEXT at call time — `package.json`, `pnpm-lock.yaml`, (claude-code also `pnpm-workspace.yaml`), `index.mjs`, (opencode also `host-tool-mcp.mjs`); commands are the frozen-lockfile install plus a version probe (`pnpm install --frozen-lockfile --store-dir .pnpm-store`, then e.g. `./node_modules/.bin/claude --version`).

### Decisive source
```ts
// claude-code-bootstrap.ts :1–16 — the placement rationale, verbatim
/*
 * Bootstrap is derived state stored under the sandbox's default working
 * directory so snapshot-capable providers can preserve the installed CLI,
 * bridge, and recipe marker without requiring root filesystem access.
 *
 * The session work dir (`startOpts.sessionWorkDir`) and the bridge-state dir
 * derived from `sandboxSession.defaultWorkingDirectory` both live under the sandbox's
 * default working directory — the provider's persistent mount — so the
 * workdir's CLI state (Claude's `~/.claude/projects/<dir>/*.jsonl` thread
 * history is keyed by working directory) and the bridge state files survive
 * both detach -> attach/replay and stop -> snapshot -> resume cycles.
 */
export const CLAUDE_CODE_BOOTSTRAP_DIR = '.harness-bootstrap/claude-code';

// :53–69 — the two-candidate resolution, identical in all four dialects
async function readBridgeAsset(name: string): Promise<string> {
  const candidates = [
    new URL(`./bridge/${name}`, import.meta.url),
    new URL(`../bridge/${name}`, import.meta.url),
  ];
  let lastErr: unknown;
  for (const url of candidates) {
    try { return await readFile(fileURLToPath(url), 'utf8'); }
    catch (err) {
      const code = (err as NodeJS.ErrnoException).code;
      if (code !== 'ENOENT') throw err;   // non-missing errors are NOT tolerated
      lastErr = err;
    }
  }
  throw lastErr ?? new Error(`bridge asset not found: ${name}`);
}
```

**Flow:** first call reads all assets in one `Promise.all`, builds the recipe object, memoizes it in a module-level `let cachedBootstrap`, and returns it; every later call in the process is a pointer check. The recipe is handed to the provider through `getBootstrap` in the harness definition; the shared kernel (pass-14 `harness-bootstrap-marker-idempotency.md`) hashes it into the sandbox identity and applies it once per content-hash. Deepagents alone prepends a conditional ripgrep install command — a single shell line that checks `command -v rg`, selects the arch tarball (`aarch64-unknown-linux-gnu` vs `x86_64-unknown-linux-musl`), downloads the pinned 14.1.1 release, verifies the per-arch SHA-256 (`echo "$sha  $f" | sha256sum -c -`), extracts, and moves `rg` into `/usr/local/bin` — because "DeepAgents' grep shells out to `rg`. Without it, the fallback reads the entire workdir, including node_modules, into memory and can run out of memory. The checksum-verified installation is skipped when `rg` exists."
**Invariant:** assets are read from the PACKAGE's own directory graph (never fetched, never generated), memoized per process, and placed under `.harness-bootstrap/<name>/` INSIDE the sandbox's persistent default working directory — the same mount that holds session work dirs — so the content-hash identity (which includes file contents) is stable across detach/attach and stop/snapshot/resume; ENOENT across both candidate layouts is the only tolerated read failure.
**Probe:** NO dedicated bootstrap test file exists in any of the four dialect packages (checked: `find packages/harness-* -name "*bootstrap*" -name "*.test.*"` → empty) — coverage caveat: deterministic-read-only, behavior pinned indirectly through the pass-14 marker-idempotency tests (`prepare-sandbox-for-harness.test.ts:108`, `harness-agent.test.ts:1857`). Deterministic probes executed at pin: `grep -c "readBridgeAsset" packages/harness-claude-code/src/claude-code-bootstrap.ts` → `5` (4 reads + 1 def); `grep -n "RIPGREP_SHA256_X64 =" packages/harness-deepagents/src/deepagents-bootstrap.ts` → :17; `grep -n "getBootstrap: get" packages/harness-codex/src/codex-harness.ts` → :198.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getClaudeCodeBootstrap readBridgeAsset bootstrapDir harness files commands", limit: 10 });
```
Graph MCP absent this session — file-level analog: naive "bootstrap" queries hit only the pass-14 marker kernel files; GREEN: each `get<Name>Bootstrap` symbol resolves to exactly one defining file, and `readBridgeAsset` appears verbatim-identical in all four (deliberate duplication, one per package, matching the repo's dependency-direction hygiene precedent from pass 14).

## Verdict
Adopt: cached-singleton recipes, two-candidate `import.meta.url` asset resolution with ENOENT-only tolerance, persistent-mount placement under a namespaced bootstrap dir, frozen-lockfile install + version-probe commands. Adapt asset lists and the install command to your bridge's build outputs. Omit the ripgrep bootstrap unless your runtime shells out to a binary that may be missing.
