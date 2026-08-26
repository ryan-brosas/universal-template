<!-- capsule-v2 -->
# Literal site harvest — where do joinable literal SITES come from before the join index, and how do non-code config files join the graph?

**Source:** pi-fovea MIT `main@5bd4e6f5c56190fb174245266464607b11f7a337`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** The literal-join index needs (file, line, text) sites, but YAML/JSON/TOML/env files cannot be parsed as code — how does pi-fovea harvest route paths and env keys from both code strings and bare config scalars without flooding the index?

## Connected graph-selected seam
**Path/Symbol:** `src/core/extract.ts:extractConfigLiterals/completeLiterals/STRING_PATTERNS` (:397–502); shared token vocabulary `PATH_TOKEN_RE/ENV_TOKEN_RE` (:408–409).
**Signature:** `extractLiterals(files, cwd, source?): Promise<LiteralSite[]>`; internal `extractConfigLiterals(files, cwd, source)` at `SOURCE_SCAN_CONCURRENCY = 8`.
**Data Shape:** `LiteralSite {file, line, text}`; text bounds enforced everywhere: quoted captures 2–200 chars (`QUOTED_RE`, `stripQuotes`), template bodies ≥2 chars, dedupe key `file|line|text`.

### Decisive source
```ts
// Config files can't be parsed as code; scan quoted strings plus bare
// path/env-shaped scalars so OpenAPI paths and k8s env keys still join.
const CONFIG_BARE_RE = /(^|[:=\s])(\/[\w.~+\-{}*]+(?:\/[\w.~+\-{}*]+)+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)(?=$|[:=\s])/g;
```

**Flow:** code files get string-literal matches from per-language `STRING_PATTERNS` via pattern runs → every code file additionally sweeps backtick templates with `TEMPLATE_RE` → config extensions (`yaml yml json toml env tf hcl md`) get quoted strings PLUS bare scalars that already look like a path or `SCREAMING_SNAKE` env key → all sources merge through `completeLiterals` with one dedupe pass.
**Invariant:** The token classifiers (`PATH_TOKEN_RE`, `ENV_TOKEN_RE`) are EXPORTED and reused by `join.ts:classifyLiteral` and `discover.ts` harvest — one vocabulary decides "is this a route/env" across harvesting, joining, and discovery; config bare scalars must pass the same classifiers downstream, so widening them here changes join edges too. Per-line `seenLine` set stops duplicate emission within a file.
**Probe:** `tests/extract.test.ts` ("extracts literals from code and config files") — asserts `/api/users/:id@server/main.go`, `/api/users/{id}@openapi.yaml`, and `DATABASE_URL@server/config.go` all land; run `pnpm vitest run tests/extract.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "extractConfigLiterals completeLiterals PATH_TOKEN_RE ENV_TOKEN_RE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-source harvest (pattern-run strings + template sweep + config bare-scalar scan), the 2–200 char bounds, and the single shared path/env classifier reused by every consumer. Adapt `CONFIG_EXTS` and quote dialects to your ecosystem. Omit nothing structural — but recalibrate the bare-scalar regex if your configs carry path-like values that must NOT join.
