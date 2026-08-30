<!-- capsule-v2 -->
# Dual-layer memory merge — workspace overrides global by BASENAME, not path

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** When two memory layers (global `~/.pi/memory` and workspace `<gitroot>/.pi/memory`) hold knowledge, which file wins and what exactly gets scanned?

## Layer scan (`scanDir` → `loadLayer`)
**Path/Symbol:** `pi-memory.ts:84-111` (`scanDir`), `pi-memory.ts:119-137` (`loadLayer`).
**Signature:** `async function scanDir(dirPath: string, prefix: string): Promise<{relPath, filePath}[]>`; `async function loadLayer(layerDir: string, source: "global"|"workspace", config: MemoryConfig): Promise<MemoryFileEntry[]>`.
**Data Shape:** `MemoryFileEntry = { relPath, content, injected, source }` where `relPath` is `"file.md"` or `"sub/file.md"` (exactly ONE level of subdirectory recursion), `content` is raw text, `injected` is the truncated copy used for prompt injection.

### Decisive source
```ts
if (entry.name.startsWith(".") || entry.name === "inbox" || entry.name === "archive" || entry.name === "state") continue;
const fullPath = path.join(dirPath, entry.name);
if (entry.isFile() && entry.name.endsWith(".md")) {
  const stat = await fs.stat(fullPath);
  if (stat.size > 0) results.push({ relPath: entry.name, filePath: fullPath });
} else if (entry.isDirectory()) {
  const subFiles = await fs.readdir(fullPath);        // one level only, no recursion
  ...
}
```
```ts
const raw = await tryReadFile(s.filePath);
if (!raw || !raw.trim()) continue;                     // whitespace-only files are dropped
files.push({ ..., injected: truncateContent(raw, config.maxFileChars), ... });
```

**Flow:** readdir top level → skip dotfiles + `inbox/`, `archive/`, `state/` dirs → accept non-empty `.md` files → for directories, take their `.md` children (one level deep) → read each, drop empty/whitespace-only → attach `source` layer tag.
**Invariant:** `inbox/`, `archive/`, `state/` are NEVER scanned into injection (they are workflow areas: candidates, history, working state). Zero-byte or whitespace-only placeholder files are invisible to the loader — the init command's `<!-- File is empty... -->` placeholders stay dormant until a human edits them. Truncation is TAIL-RETAINED: `truncateContent` returns `"... [truncated, tail retained]\n" + content.slice(-maxChars)` — newest entries live at file bottom, so the tail wins.

## Basename override merge (`mergeLayers`)
**Path/Symbol:** `pi-memory.ts:140-159` (`mergeLayers`).
**Signature:** `function mergeLayers(globalFiles: MemoryFileEntry[], workspaceFiles: MemoryFileEntry[]): MemoryFileEntry[]`.
**Data Shape:** input two tagged arrays; output merged array preserving global-first ordering minus overridden files, then all workspace files appended.

### Decisive source
```ts
const wsKeys = new Set<string>();
for (const f of workspaceFiles) wsKeys.add(path.basename(f.relPath));
// Global files: skip if workspace has a file with same basename
for (const f of globalFiles) {
  if (!wsKeys.has(path.basename(f.relPath))) merged.push(f);
}
```

**Flow:** collect workspace basenames into a Set → pass through global files whose basename is absent → append every workspace file.
**Invariant:** Override key is `path.basename(relPath)` — global `knowledge/decisions.md` is replaced by workspace `decisions.md` even though the subdirectory paths differ. Workspace ALWAYS wins; there is no field-level merge, no concatenation — whole-file replacement. Unique-name files from both layers coexist.
**Probe:** NO upstream tests exist. Pass-3 audit executed probe (`node /tmp/piext-pime-pass3/probe.mjs`, Node v26.7.0, verbatim-copy of `mergeLayers` :140–159 + `truncateContent` :113–116 at pin f3b4377f, GREEN): workspace `decisions.md` replaces global `knowledge/decisions.md` (override across DIFFERENT subdirectories) while global `user/prefs.md` survives alongside (unique-name coexistence); tail-retention quartet re-GREEN (tail kept / head dropped / marker prepended / short content untouched). Mechanical anchors: `grep -c 'wsKeys' pi-memory.ts` = **3** (:145 decl, :146 add, :152 has-check); exclusion guard line :92 greps exactly 1 for `startsWith`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory-extension", query: "mergeLayers loadLayer scanDir", limit: 10, fields: ["signature", "name", "file"] });
```
(Graph resolves all four symbols at `pi-memory.ts:84-111/119-137/140-159`; `check_index_coverage` = `no_recorded_issue`.)

## Verdict
Adopt the basename-keyed whole-file override, the inbox/archive/state scan exclusions, the empty-file dormancy rule, and tail-retained truncation. Adapt directory conventions and `maxFileChars` (4000 default) to the host. Omit nothing behavioral — but note the direct-test caveat honestly: **this repo ships NO test suite** (no test dir, no runner in package.json); the probe below pins behavior to exact source lines instead. Re-read `pi-memory.ts:92,113-116,144-158` when porting.
