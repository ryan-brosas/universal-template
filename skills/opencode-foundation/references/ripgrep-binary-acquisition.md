<!-- capsule-v2 -->
# Ripgrep binary acquisition ladder — PATH probe, managed cache, pinned download

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how do you guarantee a native search binary at runtime without bundling it, across platforms with different archive formats?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/ripgrep/binary.ts`: `RipgrepBinary.filepath` (Effect.cached body, ~:76-125), `extract` (:52-74), `PLATFORM` map (:17-26).
**Signature:** `filepath: Effect<string, Error>` (cached — resolved once per process).
**Data Shape:** 7-entry `PLATFORM` map keyed `${arch}-${platform}` → {platform triple, extension: tar.gz | zip}; target `<Global.Path.bin>/rg[.exe]`; pinned `VERSION = "15.1.0"`.

### Decisive source
```ts
filepath: yield* Effect.cached(
  Effect.gen(function* () {
    const system = yield* Effect.sync(() => which(process.platform === "win32" ? "rg.exe" : "rg"))
    if (system && (yield* fs.isFile(system).pipe(Effect.orDie))) return system
    const target = path.join(Global.Path.bin, `rg${process.platform === "win32" ? ".exe" : ""}`)
    if (yield* fs.isFile(target).pipe(Effect.orDie)) return target
    const config = PLATFORM[platformKey]
    if (!config) throw new Error(`unsupported platform for ripgrep: ${platformKey}`)
    ...
    if (bytes.byteLength === 0) throw new Error(`failed to download ripgrep from ${url}`)
```

**Flow:** (1) probe `rg` on PATH and verify it is a file → (2) reuse the managed copy in the global bin dir → (3) download the pinned release from BurntSushi GitHub for the arch-platform tuple (musl triple for x64-linux, msvc zip for windows) → extract via `tar -xzf` or PowerShell `Expand-Archive` (single quotes escaped by doubling, progress suppressed) → verify the expected `ripgrep-<ver>-<platform>/rg` exists inside → copyFile to target + chmod 0755 on non-windows → remove the archive (ignore failure). The whole ladder is `Effect.cached`, so the probe/download happens once per process even under concurrent callers.
**Invariant:** a zero-byte download is rejected; the extracted archive must contain the exact expected executable name or the ladder fails — no silent fallback to a broken binary; unsupported platform fails loudly instead of guessing.
**Probe:** `packages/core/test/ripgrep.test.ts` (3 it.live pin the Ripgrep.Service consumer: gitignore-aware find, `.git` excluded but `.opencode` included, surrogate-pair-safe 2000-char line previews) — the binary ladder itself has no direct test at this pin (download/extract paths are environment-dependent); source-confirmed only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "opencode", query: "RipgrepBinary filepath Effect.cached PLATFORM extract", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-rung ladder (PATH → managed cache → pinned download) with Effect.cached single-flight for any optional native binary. Adapt the extraction commands and platform map to your target matrix. Omit the PowerShell quoting dance if you never target Windows. Coverage caveat: no direct test pins the download/extract rungs (network-dependent); the search behavior above the binary is test-pinned.
