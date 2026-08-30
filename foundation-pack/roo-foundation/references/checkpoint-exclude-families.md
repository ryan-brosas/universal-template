<!-- capsule-v2 -->
# checkpoint exclude patterns — what never enters a shadow-git checkpoint, and how is the list assembled?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Which paths must a per-task checkpoint snapshot ignore, and where does the only dynamic part of that list come from?

## Nine static pattern families + one dynamic .gitattributes reader
**Path/Symbol:** `src/services/checkpoints/excludes.ts:getExcludePatterns` (lines 201–212) + family builders :6–199 (`getLfsPatterns` :186).
**Signature:** `getExcludePatterns(workspacePath: string): Promise<string[]>`; `getLfsPatterns(workspacePath: string): Promise<string[]>` (private).
**Data Shape:** gitignore-style patterns: dir forms carry trailing `/` (`.git/`, `node_modules/`, `dist/`, `__pycache__/`, `target/dependency/`…); file globs are `*.ext` (media ×38, cache ×18, large-data, database, geospatial, log families); config family is `*.env*`, `*.local`, `*.development`, `*.production`.

### Decisive source
```ts
export const getExcludePatterns = async (workspacePath: string) => [
	".git/",
	...getBuildArtifactPatterns(),
	...getMediaFilePatterns(),
	...getCacheFilePatterns(),
	...getConfigFilePatterns(),
	...getLargeDataFilePatterns(),
	...getDatabaseFilePatterns(),
	...getGeospatialPatterns(),
	...getLogFilePatterns(),
	...(await getLfsPatterns(workspacePath)),
]
```

**Flow:** static families concatenated with `.git/` first; then `.gitattributes` is read and every line containing `filter=lfs` contributes its FIRST whitespace-separated field (the path/glob spec) as an exclude — so LFS-tracked artifacts never enter checkpoints. Any read error → empty array (silent).
**Invariant:** the ONLY dynamic input is .gitattributes LFS lines; everything else is compile-time constant. Duplicates are possible by design (`*.bak` appears in BOTH cache and database families; `*.csv` in both database and geospatial; `*.log` in cache and log families) because consumers pass the array to git's ignore machinery where repeats are harmless — deduping would be wasted work but porters copying single families will silently under-exclude. `*.env*` excludes ALL env files including `.env.example`-style names.
**Probe:** `grep -c 'filter=lfs' src/services/checkpoints/excludes.ts` → 1; `grep -c 'getGeospatialPatterns' src/services/checkpoints/excludes.ts` → 2; `grep -cF '"*.csv"' src/services/checkpoints/excludes.ts` → 2 (cross-family dup proof).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "getExcludePatterns getLfsPatterns gitattributes checkpoint", limit: 10 });
```

## Verdict
Adopt the family decomposition and the LFS-from-.gitattributes dynamic leg; keep duplicates (they're consumed by git). Adapt family contents to your host's ecosystem. Direct test: `src/services/checkpoints/__tests__/excludes.spec.ts` (describe "getExcludePatterns" :20, "getLfsPatterns" :27 incl. no-patterns :62 / missing-file :96 / read-error :124 cases). Companion note: `RepoPerTaskCheckpointService.ts` (15L) is just `ShadowCheckpointService` rooted at `shadowDir/tasks/<taskId>/checkpoints` — the per-task variant differs from the shared-repo twin ONLY in that path join.
