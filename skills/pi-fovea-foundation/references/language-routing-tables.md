<!-- capsule-v2 -->
# Language routing tables — which parser tier does a file get, and how does an old extractor version fail honestly?

**Source:** pi-fovea MIT `main@5bd4e6f5c56190fb174245266464607b11f7a337`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** A multi-language engine needs full symbol/call extraction for some languages, symbols-only for others, and regex-only literal joins for non-code — where is that partition decided, and what happens when the installed binary predates a structured interface?

## Connected graph-selected seam
**Path/Symbol:** `src/core/astgrep.ts:LANG_BY_EXT/isBinaryExt/isConfigFile/groupByLang` (:14–41, :177–197); fallback contract `outlineStructured` (:249–270).
**Signature:** `langOf(file): string | undefined`; `groupByLang(files): Map<string, string[]>`; `outlineStructured(files, _lang, cwd): Promise<OutlineFile[] | undefined>`.
**Data Shape:** `LANG_BY_EXT` maps ~30 extensions to language names in two tiers — first tier (ts/tsx/js/jsx variants, py, go, rs) gets pattern-based call/import extraction; second tier (Elixir, Ruby, C/C++, Java, Kotlin, Lua, Php, Swift, Scala, Haskell, Bash) gets outline symbols only with heuristic name derivation. `CONFIG_EXTS` (yaml/yml/json/toml/env/tf/hcl/md) routes to regex-only literal harvest; `BINARY_EXTS` excludes compiled artifacts.

### Decisive source
```ts
// Expanded JSON preserves each member's own range and signature. Return
// undefined when the installed ast-grep predates this interface so callers can
// fall back without presenting parent locations as exact member locations.
export const outlineStructured = async (files: string[], _lang: string, cwd: string): Promise<OutlineFile[] | undefined> => {
  ...
  // A subprocess failure here is NOT recorded: extractSymbols falls back to
  // the text outline for old ast-grep versions, and that text run is what
  // records a genuine failure (old versions must not read as failures).
```

**Flow:** every file enters exactly one pipeline via its extension — binary excluded, config → literal harvest, tier-1 language → structured outline + consolidated fact scan, tier-2 language → text/structured outline symbols only → `groupByLang` partitions files so each ast-grep invocation handles one language batch.
**Invariant:** The structured-outline path returns `undefined` (never throws, never records a failure) when output is empty/unparseable so legacy binaries fall back to the text outline; only the TEXT run records ExtractionFailure — capability absence must not pollute the honesty ledger. Outline-derived members carry `lineApproximate` and the renderer prints "(member line unavailable)" rather than a false exact line.
**Probe:** `tests/extract.test.ts` ("extracts symbols across Go, TypeScript and Python via outline" pins exact lines + `lineApproximate` falsity for expanded JSON; "normalizes variable items whose name inlined a huge C initializer" pins the 256-char name bound against outline blowups); run `pnpm vitest run tests/extract.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "LANG_BY_EXT groupByLang outlineStructured isConfigFile isBinaryExt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the extension-tier routing table, the one-language-per-invocation batching, and the undefined-fallback honesty contract for capability drift. Adapt the tier membership to your parser set. Omit ast-grep's specific `outline --json=compact --view=expanded` flags if your extractor has one stable interface.
