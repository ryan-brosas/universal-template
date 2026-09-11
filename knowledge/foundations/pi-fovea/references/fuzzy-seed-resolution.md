<!-- capsule-v2 -->
# Fuzzy seed resolution — how does "switchServer" find switchingServers and "/api/airports" find everything mounted below it?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Model queries are approximate (camelCase variants, inflections, route prefixes, typos) — what is the resolution ladder from exact match down to suggestions, and how do misses avoid dead ends?

## Five-tier ladder ending in Dice-similarity suggestions
**Path/Symbol:** `src/core/ops.ts:resolveSeeds/identifierTerms/stemIdentifier/symbolSimilarity/sameIdentifierTerms/diceSimilarity/matchesFocusScope` (:372-539); miss renderer `focus()` (:770-806).
**Signature:** `resolveSeeds(state, query, options): {seeds: number[], note: string, suggestions: SeedSuggestion[]}`; top 16 seeds; suggestion floor `score ≥ 0.34`, top 5.
**Data Shape:** Identifier terms: camelCase/snake split → lowercase → stop-word filter ("what/where/how/find…") → light stemming (ing/ies/es/s) → dedupe. Symbol similarity = `max(0.72·coverage + 0.28·precision, dice(bigrams))`.

### Decisive source
```ts
// Literal route: treat the query itself as a join token (path/env/word).
const cls = classifyLiteral(q);
if (cls === "path") {
  // Route-prefix queries ("/api/airports") seed everything mounted below them
  // — the query is rarely a literal in code, which is the point: the model
  // shouldn't have to guess the full route string to look at it.
  const under = `${norm}/`;
  for (const [key, bucket] of state.joinIndex.byKey)
    if (bucket.cls === "path" && key.startsWith(under)) bucket.occ.forEach(o => bump(o.node, 0.8));
  state.graph.nodes.forEach((n, i) => {
    if (n.kind !== "anchor") return;
    const route = n.name.slice(n.name.indexOf(" ") + 1);
    if (route === norm || route.startsWith(under)) bump(i, 0.9);
  });
}
// Tier ladder: exact byName hits (1) → substring exact/prefix/includes (1/.8/.5)
// → same-identifier-terms inflections (.7) → file-path suffix (1)
// → on TOTAL miss: ranked Dice suggestions instead of an empty answer.
const suggestions = g.nodes.map((node, i) => ({node, index: i, score: symbolSimilarity(q, node)}))
  .filter(s => s.score >= 0.34 ...).slice(0, 5);
```

**Flow:** literal classification → name-index terms → substring fallback → inflection equivalence (`switchServer` ≡ `switchingServers`: both term-split+stem to {switch, server}s) → path-suffix files → if still empty, nearest symbols render as "? name — location — sig" plus retry guidance, budgeted by shrinking the suggestion count until it fits. All bumps respect `matchesFocusScope` (path/language/kind) so scoped focuses never hide their target.
**Invariant:** A no-certain-match query must NEVER return an empty answer — suggestions carry locations and signatures. Seeds cap at 16; scores below 1 render "(approximate)" in the note. Fresh focus resets disclosure and t=2; repeated identical queries keep nucleus + suppress periphery.
**Probe:** `tests/ops.test.ts` — "recovers equivalent camelCase and inflected symbol queries" (`loadsUsers`→loadUser, `switchServer`→ClientConnection.switchingServers at web/server-switcher.ts:2); "suggests nearby symbols when a typo cannot seed the graph" (loadUsr → Nearby symbols); "focus on a route resolves across languages within budget" (/api/users/{id} hits Go+TS+YAML).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "resolveSeeds identifierTerms symbolSimilarity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tiered resolution ladder, the term-split+stem equivalence, route-prefix descendant seeding, and the never-empty miss contract with scored suggestions. Adapt stems/stop words to your language audience. Omit the specific stop-word list's opinionated entries if porting beyond coding agents.
