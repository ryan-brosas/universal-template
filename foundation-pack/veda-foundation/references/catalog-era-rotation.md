<!-- capsule-v2 -->
# Catalog-era rotation — how do you invalidate learned state automatically whenever the underlying catalog content changes?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** How do you version a persistent learned-state store so that editing any prompt in the catalog starts a fresh learning namespace — without migration scripts or manual bumping?

## Connected graph-selected seam
**Path/Symbol:** `src/core/era.ts:computeCatalogDigest` (:19–34), `deriveEraId` (:36–38), `getCurrentEra` (:40–43), plus the key-suffix grammar `isEraNamespaced`/`extractEraFromKey`/`stripEraSuffix`/`addEraSuffix` (:49–64). Module header states the contract outright: *"When any module prompt changes, the era ID changes automatically."*
**Signature:** `computeCatalogDigest(modules: ReasoningModule[]): string`; `deriveEraId(digest: string): string`; `addEraSuffix(key: string, eraId: string): string`.
**Data Shape:** `EraRef = { id: "m_" + first 12 hex of digest, catalogDigest: full sha256 hex }` (from `src/stats/pairwise-types.ts`). Keys are suffixed `<baseKey>@m_[a-f0-9]{12}`.

### Decisive source
```ts
function normalizePrompt(prompt: string): string {
  return prompt.replace(/\r\n/g, '\n').replace(/[ \t]+$/gm, '').trim();
}
export function computeCatalogDigest(modules: ReasoningModule[]): string {
  const sorted = [...modules].sort((a, b) => {
    const catCmp = a.category.localeCompare(b.category);
    if (catCmp !== 0) return catCmp;
    return a.id.localeCompare(b.id);
  });
  const canonical = sorted.map(m => ({ id: m.id, category: m.category, name: m.name, prompt: normalizePrompt(m.prompt) }));
  return createHash('sha256').update(JSON.stringify(canonical)).digest('hex');
}
```

**Flow:** sort modules by (category, id) → canonicalize each to `{id, category, name, whitespace-normalized prompt}` → sha256 over the JSON → era id = `m_` + 12-hex prefix → stats writers suffix every entity key and opponent key with `@<eraId>`; readers select by era.
**Invariant:** order independence (declaration order or array reshuffles never rotate the era); whitespace-only edits (CRLF, trailing spaces) never rotate it; *any* semantic prompt/name/category/id change always does; the regexes `/@m_[a-f0-9]{12}$/` are the single source of truth for what counts as namespaced.
**Probe:** no dedicated upstream test (verified: zero direct references to `era.ts` symbols in `tests/`). Deterministic source-pinned probe executed at pin: the module's own doc-comment contract + `deriveEraId("abc…") = "m_" + slice(0,12)` is directly checkable from the served snippet; downstream consumer behavior is pinned live by `bun src/core/design/__probe__.ts`-style execution only for design — for era, the executable owned evidence is the ratings/pairwise suites' green run (`tests/stats/store.test.ts` 7 pass) which exercises the same snapshot file family.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "computeCatalogDigest deriveEraId addEraSuffix stripEraSuffix currentEra", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt content-addressed era rotation for any learned/accumulated state keyed to a mutable catalog: canonical-sort + normalize + hash + short id + key-suffix grammar. Adapt the hash input fields and the id prefix to your domain. Omit Veda's specific module shape. Caveat: no upstream direct test pins this file — treat the regex/slice contracts above as source-derived, and keep `getCurrentEra()` reading from one registry constant (`DEFAULT_REGISTRY.modules`) so there is exactly one era authority per process.
