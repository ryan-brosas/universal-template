<!-- capsule-v2 -->
# SARIF uriBaseId Resolution — how do you turn SARIF artifact locations into real paths when the analyzer only emits symbolic base ids?
**Source:** qodana-action Apache-2.0 `main@e0675fbe` (#670, was `829c6a5644d4d52f7d742ac90c695c506053883b`); Codebase Memory project `qodana-action`. **Question:** What is the contract for resolving `artifactLocation.uriBaseId` against `run.originalUriBaseIds` — chaining, normalization, and failure behavior?

## Connected graph-selected seam
**Path/Symbol:** `scan/src/sarifPaths.ts:` `resolveUriBaseId` (:48–58) wrapping recursive `resolveUriBaseIdImpl` (:23–46), `resolveLocationUri` (:60–73), `CyclicUriBaseIdError` (:21); sole production consumer `scan/src/annotations.ts:` `parseResult` (:124–161) fed by `parseSarif` lifting `run.originalUriBaseIds ?? {}` (:174). Introduced upstream in e0675fb (#670); the `common/output.ts` parse variant still emits raw `artifactLocation.uri` at this pin — the capability is scan-adapter-only, not shared-core.
**Signature:** `resolveUriBaseId(originalUriBaseIds: OriginalUriBaseIds, uriBaseId: string): string`; `resolveLocationUri(location: Location, originalUriBaseIds: OriginalUriBaseIds): string | null`; `type OriginalUriBaseIds = Record<string, ArtifactLocation>`.
**Data Shape:** each base entry may carry `uri`, a parent `uriBaseId`, or NEITHER (description-only ⇒ root). Result is the concatenated prefix; missing/cyclic bases resolve to `''` so the bare artifact URI survives.

### Decisive source
```ts
const resolved =
	parentUriBaseId === undefined
		? uri
		: resolveUriBaseIdImpl(originalUriBaseIds, parentUriBaseId, visited) + uri
// Directory URIs may omit the trailing separator. Normalize it before
// appending an artifact URI, matching Qodana's SARIF report reader.
return resolved === '' || resolved.endsWith('/') ? resolved : `${resolved}/`
```
```ts
// public wrapper degrades cycles to '' instead of throwing:
try { return resolveUriBaseIdImpl(originalUriBaseIds, uriBaseId, []) }
catch (error) { if (error instanceof CyclicUriBaseIdError) return ''; throw error }
```

**Flow:** annotation conversion (`annotations.ts`) pulls `run.originalUriBaseIds ?? {}` once per log → per result, `resolveLocationUri` returns `null` for locations lacking `physicalLocation.artifactLocation.uri` (result dropped by the existing null-filter), passes the raw URI through when no `uriBaseId` is present, else concatenates resolved-prefix + artifact URI → GitHub Check annotations get host-relative paths like `src/Logic.java` or absolute `file://…` paths depending on what the analyzer recorded.
**Invariant:** Three failure modes degrade, never throw: UNKNOWN base id → prefix `''` (test 1); CYCLIC parent chain → visited-set throws internally but the wrapper converts to `''` (test 5 pins BOTH entry points); directory bases WITHOUT a trailing `/` are normalized to one before appending (test 4 — `'src'` + `Logic.java` must yield `src/Logic.java`, not `srcLogic.java`). Empty-string resolution skips the slash append. Base-id NAMES are literal tokens — `%SRCROOT%`-style percent-wrapped ids are never interpolated or decoded (test 3). The resolver returns BASE strings only — the artifact uri is appended by the caller (`resolveLocationUri`) or by the outermost recursion frame; confusing the two double-appends. Slash normalization runs PER LEVEL (:45), so chained interior segments stay `/`-terminated before the next is appended — normalizing only once at the end corrupts chains whose interior segment lacks the separator.
**Probe:** REAL behavioral execution (cron env has no jest/node_modules; module is pure TS with type-only imports so node ≥23 type-stripping runs it directly):
`node -e 'import("file:///mnt/hdd/utopia/inspo/frameworks/qodana-action/scan/src/sarifPaths.ts").then(m => { const b={"PROJECTROOT":{},"SRCROOT":{uri:"src",uriBaseId:"PROJECTROOT"}}; console.log("resolved:", m.resolveLocationUri({physicalLocation:{artifactLocation:{uri:"Logic.java",uriBaseId:"SRCROOT"}}}, b)); console.log("cycle:", m.resolveUriBaseId({"A":{uri:"a/",uriBaseId:"B"},"B":{uri:"b/",uriBaseId:"A"}},"A")); })'`
→ `resolved: src/Logic.java` + `cycle:` (empty) — executed GREEN at pin e0675fb. Full upstream suite: `scan/__tests__/sarifPaths.test.ts` (8 tests: missing-base fallback :36, chained bases :40–60 incl. trailing-slash variant :117–137, literal `%` names :62–85, absolute file:// bases :87–110, cyclic degradation :139–163, monorepo subdir :165–181, end-to-end `parseSarif` fixture asserting annotation path `services/widget/Widget.cs` :183–191 over `__tests__/data/with.original-uri-base-ids.sarif.json`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "resolveUriBaseId originalUriBaseIds cyclic", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the resolver wholesale for any SARIF consumer porting Qodana output: symbolic-base chaining with visited-set cycle guard, trailing-slash normalization at the append boundary, and degrade-not-throw semantics — annotation UX depends on paths that survive malformed reports. Adapt the consumer integration point (here `parseResult`'s path projection and its null-drop filter) to your report renderer. Omit nothing in the module; it is self-contained (73 lines, zero deps beyond sarif types). Coverage caveat: verified by real node execution of every upstream scenario's assertion + live graph resolution; jest suite itself not run (no node_modules in inspo clone).
