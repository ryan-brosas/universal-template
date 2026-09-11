<!-- capsule-v2 -->
# LSP language spawn ladders — how do you make per-language server availability honest (never crash, never double-download, never escape the workspace)?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** The fleet contract (lsp-client-fleet.md) is `spawn(root) → Handle | undefined`. What do the concrete ladders underneath it look like for languages that need custom root discovery, binary download, or extension-host artifacts — and what does "honest availability" mean at each step?

## RustAnalyzer: workspace-root walk
**Path/Symbol:** `packages/opencode/src/lsp/server.ts` `RustAnalyzer` :890-934.
**Signature:** `root(file, ctx) → Promise<string | undefined>`; `spawn(root) → Handle | undefined` via `which("rust-analyzer") or undefined`.
**Data Shape:** root = NearestRoot(["Cargo.toml","Cargo.lock"]) crate root, upgraded to the nearest ancestor Cargo.toml containing `[workspace]`.

### Decisive source
```ts
// server.ts:891-915 — crate root, then walk UP for a workspace marker, bounded
const crateRoot = await NearestRoot(["Cargo.toml", "Cargo.lock"])(file, ctx)
if (crateRoot === undefined) return undefined
let currentDir = crateRoot
while (currentDir !== path.dirname(currentDir)) {          // stop at filesystem root
  const cargoTomlContent = await Filesystem.readText(path.join(currentDir, "Cargo.toml"))
  if (cargoTomlContent.includes("[workspace]")) return currentDir
  ...
  currentDir = path.dirname(currentDir)
  if (!currentDir.startsWith(ctx.worktree)) break          // never escape the app root
}
return crateRoot                                            // fall back to crate root
```

**Flow:** find the crate root; walk ancestors looking for a `[workspace]` section; the walk is bounded by the filesystem root AND ctx.worktree (never escapes the app root); no workspace marker → serve from the crate root. spawn is which-or-undefined — no download.
**Invariant:** the returned root is always inside the worktree; unavailability is `undefined`, never a throw.
**Probe:** no direct test pins this ladder (grep of packages/opencode/test/lsp/ = 0 references — coverage caveat, source-confirmed only); the NearestRoot marker-walk machinery it composes is pinned by `test/lsp/jdtls-root.test.ts` (24 tests). Source pin:
```bash
grep -n 'includes("\[workspace\]")' packages/opencode/src/lsp/server.ts   # expect 1 (:904)
```

## Clangd: discovery + download ladder
**Path/Symbol:** `packages/opencode/src/lsp/server.ts` `Clangd` :935-1068.
**Signature:** `spawn(root, _ctx, flags) → Handle | undefined`; args `["--background-index", "--clang-tidy"]`.
**Data Shape:** discovery order PATH → `Global.Path.bin/clangd<ext>` direct → `clangd_<tag>/bin/clangd<ext>` scan → GitHub releases/latest download.

### Decisive source
```ts
// server.ts:1000-1012 — platform-token asset selection, priority zip > tar.xz > any
const tokens: Record<string, string> = { darwin: "mac", linux: "linux", win32: "windows" }
const valid = (item) => item.name?.includes(token) && item.name?.includes(tag)
const asset =
  assets.find((item) => valid(item) && item.name?.endsWith(".zip")) ??
  assets.find((item) => valid(item) && item.name?.endsWith(".tar.xz")) ??
  assets.find((item) => valid(item))
```

**Flow:** every discovery step returns undefined on failure (honest availability). Download path: fetch releases/latest, map platform to asset token, pick by priority, download, extract (extractZip or tar -xf), rm archive, chmod 0o755 (non-win32), re-point the bare `clangd` symlink at the versioned dir, spawn from the versioned path. `flags.disableLspDownload` gates ONLY the download step — local discovery still runs first.
**Invariant:** never double-download (direct + versioned-dir scans precede the fetch); every failure mode yields undefined; the symlink swap makes the next run hit the direct-path fast path.
**Probe:** no direct test pins this ladder (same coverage caveat); fleet contract around it pinned by `test/lsp/index.test.ts` + `lifecycle.test.ts`. Source pin:
```bash
grep -c 'disableLspDownload' packages/opencode/src/lsp/server.ts   # expect 27
grep -c 'clangd_' packages/opencode/src/lsp/server.ts   # expect 2
grep -n 'background-index' packages/opencode/src/lsp/server.ts   # expect 1 (:940)
```

## Roslyn/Razor: single-flight install + extension artifacts
**Path/Symbol:** `packages/opencode/src/lsp/server.ts` `Razor` :703-727, `getRoslynLanguageServer` :737-748, `installRoslynLanguageServer` :750-775, `roslynLanguageServerGlobalPath` :777-784, `findVscodeRazorExtension` :787-821.
**Signature:** module-level `roslynLanguageServerInstall: Promise<string | undefined> | undefined` single-flight.
**Data Shape:** Razor spawn needs THREE artifacts: roslyn binary + razor compiler dll + design-time targets + extension dll (from the C# extension).

### Decisive source
```ts
// server.ts:744-746 — single-flight install promise, cleared on settle
roslynLanguageServerInstall ||= installRoslynLanguageServer(disableLspDownload).finally(() => {
  roslynLanguageServerInstall = undefined
})
```

**Flow:** which → DOTNET_CLI_HOME (or home)/.dotnet/tools global path → single-flight `dotnet tool install --global roslyn-language-server --prerelease` (gated by which("dotnet") AND disableLspDownload). findVscodeRazorExtension scans VSCODE_EXTENSIONS + ~/.vscode{,-insiders,-server,-server-insiders}/extensions for `ms-dotnettools.csharp-*` dirs, picks the NEWEST by mtime, and requires all three artifacts to exist — any miss → undefined.
**Invariant:** concurrent spawns share one install promise (no duplicate dotnet installs); a missing extension artifact means unavailable, not a partial spawn.
**Probe:** no direct test pins this ladder (same coverage caveat). Source pin:
```bash
grep -n 'roslynLanguageServerInstall ||=' packages/opencode/src/lsp/server.ts   # expect 1 (:744)
grep -n 'ms-dotnettools.csharp-' packages/opencode/src/lsp/server.ts   # expect 1 (:800)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "RustAnalyzer Clangd Roslyn spawn ladder disableLspDownload single-flight NearestRoot workspace", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three availability patterns: which-or-undefined, bounded workspace-root walks, and discovery-before-download with a single-flight install promise; adopt "every failure yields undefined" as the fleet contract's meaning. Adapt platform token maps and archive handling to your distribution story; omit the GitHub download path entirely if you ship servers yourself. COVERAGE CAVEAT: no direct test pins any of these three ladders at this pin (0 references in packages/opencode/test/lsp/) — source-confirmed only; the surrounding fleet contract is test-pinned (pass-10 capsules). bun runner blocked at this checkout, probes are byte-exact greps.
