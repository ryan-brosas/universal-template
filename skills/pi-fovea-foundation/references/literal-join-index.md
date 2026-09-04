<!-- capsule-v2 -->
# Cross-language literal join index — how do Go servers, TS clients, YAML specs, and Rust workers become one connected graph?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Per-language symbol graphs stop at the language boundary — how do you join them through shared strings without common literals ("1-hop channel has no ranking signal") turning every hub into noise?

## IDF-graded literal bridges with placeholder normalization
**Path/Symbol:** `src/core/join.ts:classifyLiteral/normalizeLiteral/buildJoinIndex` (:21-110); consumers `src/core/ops.ts:resolveSeeds` route-prefix seeding (:458-478), `build.ts` join edges (:1009-1013).
**Signature:** `classifyLiteral(text): "path"|"env"|"word"|undefined`; `normalizeLiteral(text, cls): string`; `buildJoinIndex(sites: LiteralSite[], resolveOccurrence: (file,line)=>number|undefined): JoinIndex`.
**Data Shape:** `JoinIndex.byKey: Map<normalizedKey, {cls, spec∈[0,1], occ[]}>`; `edges: {a,b,w}[]`. Class bases `{path:1.0, env:0.8, word:0.55}`; edge gates `df<2 || df>48` (singleton = no join; >48 files = ambient); lookup keeps up to 192 occurrences per key even for out-of-gate keys.

### Decisive source
```ts
// Router conventions disagree on placeholders (:id gin/express, {id} OpenAPI,
// ${id} templates, * wildcards). Segment-wise normalization makes them ONE token.
const PLACEHOLDER_SEGMENT = /^(?::[^/]+|\{[^}/]*\}|\$\{[^}/]*\}|\$[A-Za-z_]\w*|<[^/>]+>|\*+)$/;
export const normalizeLiteral = (text: string, cls: LitClass): string => {
  const t = text.trim();
  if (cls === "env") return t.toUpperCase();
  if (cls === "word") return t;
  const body = t.replace(URLISH_RE, "");            // strip https://origin
  return body.split("/").map((s) => PLACEHOLDER_SEGMENT.test(s) ? "{*}" : s)
    .join("/").replace(/\/$/, "");
};
// Specificity = min-maxed IDF; edge weight decays past ~6 clique members so a
// popular literal can't turn members into uncapped conductance hubs.
const spec = Math.min(1, Math.log(total / Math.max(df, 1)) / idfMax || 0);
const w = (BASE[g.cls] * (0.25 + 0.75 * spec)) / Math.max(1, df / 6);
// One occurrence per (key, file): repetition inside a single file must not
// inflate document frequency, or lockfile-ish files dominate the bridge.
if (g.seenFiles.has(s.file)) continue;
```

**Flow:** classify each extracted string → normalize to canonical join token → dedupe per (key,file), resolve to enclosing symbol node (else file node) → compute min-maxed IDF specificity → emit clique edges (pair-best kept) only for literals in the rarity band 2..48 files → weights feed the CSR as `join` edges ("shared literal" channel, sync prior 0.35).
**Invariant:** Rarity IS the ranking signal: a literal in 2 files is a strong bridge, in 30 near-noise — never emit uniform-weight join edges. Focus lookups stay liberal (`LOOKUP_CAP=192`, singletons still searchable as seeds) while EDGE construction alone enforces the band; route queries seed prefix descendants at 0.8 and matching anchors at 0.9.
**Probe:** `tests/join.test.ts` — "unifies router placeholder conventions" (`/api/users/:id` ≡ `{id}` ≡ `${id}` → `/api/users/{*}`); "weights specific literals above common ones (IDF gradation)"; "drops singletons (no spurious self-joins)". E2E: `tests/ops.test.ts` impact warms web/api.ts + openapi.yaml + worker/search.rs from a Go handler edit via "shared literal".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "buildJoinIndex normalizeLiteral classifyLiteral", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt classification + segment-wise placeholder normalization + per-(key,file) DF dedup + banded-IDF edge gating with clique decay. Adapt class regexes/bases to your literal domains (add e.g. queue/topic names). Omit nothing else; every constant here encodes a measured failure mode.
