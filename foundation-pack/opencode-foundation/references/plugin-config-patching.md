<!-- capsule-v2 -->
# Plugin config patching — how do you add a plugin to the user's JSONC config without destroying it?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How does `plugin add` write into an existing (possibly commented) config file — choosing add vs replace vs noop, and where?

## JSONC surgical patch
**Path/Symbol:** `packages/opencode/src/plugin/install.ts` (`patchPluginConfig`, `patchOne`, `patchPluginList`, lines 181-439).
**Signature:** `patchPluginConfig(input: PatchInput, dep?: PatchDeps): Promise<PatchResult>` with per-target results `{kind, mode:"add"|"replace"|"noop", file}`.
**Data Shape:** Target dir: `--global` → global config dir (or explicit `config`); else `<worktree|directory>/.opencode` (worktree only when vcs==="git" and worktree!=="/"). File ladder via `files(dir, name)`: server kind → `opencode.json|jsonc`, tui kind → `tui.json|tui.jsonc`; first EXISTING file wins, else the first candidate is created. All deps (readText/write/exists/files/resolve) injectable for tests.

### Decisive source
```ts
// install.ts:214-257 — duplicate handling inside patchPluginList
if (!force) return { mode: "noop", text }
const keep = dup[0]
...
if (dup.length === 1 && keep.spec === spec) return { mode: "noop", text }
let out = text
if (typeof keep.item === "string") out = patch(out, ["plugin", keep.i], next)
if (Array.isArray(keep.item) && typeof keep.item[0] === "string") out = patch(out, ["plugin", keep.i, 0], spec)
const del = dup.map((item) => item.i).filter((i) => i !== keep.i).sort((a, b) => b - a)
for (const i of del) out = patch(out, ["plugin", i], undefined)
```

**Flow:** acquire file lock (`Flock.acquire("plug-config:"+resolved cfg path)`) → read existing text (ENOENT → "{}") → jsonc parse collecting errors; on error report `{code:"invalid_json", line, col}` computed from byte offset → decide rows → apply edits via `modify()+applyEdits()` preserving comments/formatting → write only when mode≠noop.
**Invariant:** Duplicate detection matches on PARSED PACKAGE NAME (never on raw string), except file:// specs which must match exactly. Without `--force`, an existing same-package entry is a noop — never silently upgraded. With force, exactly ONE row survives (first duplicate kept), its spec/options replaced in place, remaining duplicates deleted in DESCENDING index order so earlier deletions don't shift later offsets. A missing `plugin` array becomes `[next]`; an existing one gets `isArrayInsertion` append at index length. Server and TUI targets patch DIFFERENT files in separate lock scopes (`plug-config:<dir>/opencode` vs `<dir>/tui`).
**Probe:** `packages/opencode/test/plugin/install.test.ts` (570L suite over modes/targets) + `packages/opencode/test/plugin/install-concurrency.test.ts` — `"serializes concurrent server config updates across processes"` (:66) and `"serializes concurrent server+tui config updates across processes"` (:89, proves the two lock scopes don't deadlock or clobber).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "patchPluginConfig patchPluginList install plugin config", limit: 8 });
```

## Verdict
Adopt lock-per-config-file + descending-index deletion + name-based dedupe-with-force as THE way tools mutate human-edited config. Adapt the jsonc library choice and file ladder names. Omit the CLI flag plumbing (`force/global/vcs`) — keep it as the dependency-injected input shape.
