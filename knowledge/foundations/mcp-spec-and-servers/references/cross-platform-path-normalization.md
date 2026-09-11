<!-- capsule-v2 -->
# Cross-platform path normalization — how do you normalize user-supplied paths across Windows/Unix/WSL/UNC without breaking fs operations?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/filesystem); Codebase Memory `servers`. **Question:** What is the ordered ladder that decides whether a path is Unix, WSL, unix-style-Windows, UNC, or drive-letter — and which conversions are FORBIDDEN?

## WSL-never-converts + platform-gated /c/ conversion + UNC preservation
**Path/Symbol:** `src/filesystem/path-utils.ts` (whole file: `convertToWindowsPath` :9–32; `normalizePath` :39–112; `expandHome` :119–124). Direct test `src/filesystem/__tests__/path-utils.test.ts` (382L).

**Signature:** `normalizePath(p: string): string` — strip surrounding quotes+whitespace → classify (WSL `/mnt/<drive>/`, unix-style Windows `/<drive>/` ONLY on win32, plain Windows `[a-zA-Z]:`) → collapse duplicate separators → bare-drive-letter guard → `path.normalize` → post-fixes (UNC leading backslashes, slash direction, drive-letter capitalization). `expandHome`: `~/x` and bare `~` join `os.homedir()`.

### Decisive source
```ts
// src/filesystem/path-utils.ts:9-23 — the forbidden conversion
export function convertToWindowsPath(p: string): string {
  // NEVER convert WSL paths - they are valid Linux paths that work with
  // Node.js fs operations in WSL. Converting them to Windows format
  // (C:\...) breaks fs operations inside WSL
  if (p.startsWith('/mnt/')) {
    return p;                                  // Leave WSL paths unchanged
  }
  // Only convert when running on Windows
  if (p.match(/^\/[a-zA-Z]\//) && process.platform === 'win32') { ... }
```

```ts
// :80-92 — the two normalization traps
// On Windows, if we have a bare drive letter (e.g. "C:"), append a separator
// so path.normalize doesn't return "C:." which can break path validation.
if (process.platform === 'win32' && /^[a-zA-Z]:$/.test(p)) p = p + path.sep;
let normalized = path.normalize(p);
// Fix UNC paths after normalization (path.normalize can remove a leading backslash)
if (p.startsWith('\\\\') && !normalized.startsWith('\\\\')) normalized = '\\' + normalized;
```

**Flow:** quotes/whitespace stripped first (:41) → WSL check short-circuits EVERYTHING (`/mnt/c/...` returns untouched on ALL platforms) → on win32, `/\d/`-style paths become `<D>:\...`; elsewhere they stay literal unix paths → double-backslash collapse preserves exactly-two leading backslashes for UNC (`\\SERVER\share`) → `path.normalize` handles `.`/`..` → drive letters capitalized (`c:/windows` → `C:\windows`), forward slashes→backslashes on win32 only.

**Invariant:** converting `/mnt/c/...` to `C:\...` BREAKS every fs operation when Node runs inside WSL (the issue #2795 fix) — this rule holds even when process.platform is win32. The same literal string changes meaning with platform: `/c/foo` is a Windows drive path ONLY on win32. Bare `C:` must gain a separator before `path.normalize` or validation sees `C:.`; UNC's leading `\\` must be re-added if normalize ate it.

**Probe:** `src/filesystem/__tests__/path-utils.test.ts` — issue #2795 reproduction mocks platform=linux and asserts no `C:`/`\` in output (:339–355); WSL preserved under BOTH win32/linux mocks (:243–277); bare drive `C:`→`C:\`, `d:`→`D:\` on win32 (:357–366); UNC doubles collapsed preserving leading pair (:194–202); quotes/spaces stripped (:71–72, :81–84); lowercase drive capitalized (:176–181).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "normalizePath convertToWindowsPath expandHome WSL", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the classification ladder verbatim — especially WSL-never-converts, platform-gated `/c/` handling, the bare-drive-letter separator guard, and UNC re-pinning — for any tool accepting filesystem paths from heterogeneous clients; adapt the allowed-root policy around it (see `filesystem-sandbox` + `roots-validation-ladder`); omit naive `path.normalize`-only normalization (breaks WSL, UNC, and `C:` inputs).
