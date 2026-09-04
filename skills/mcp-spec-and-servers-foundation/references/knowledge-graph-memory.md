<!-- capsule-v2 -->
# Knowledge-graph memory server — JSONL append-semantic store with set-like mutations behind a single tool surface

**Source:** modelcontextprotocol/servers MIT `main@76d64c8`; Codebase Memory `servers`. **Question:** How does the canonical memory server model entities/relations/observations so every mutation is idempotent and referentially safe?

## Whole-file load → filter-dedupe mutate → whole-file save; deletes cascade
**Path/Symbol:** `src/memory/index.ts` (`Entity|Relation|KnowledgeGraph` types :51–66; `KnowledgeGraphManager` :69+ — `loadGraph` :72–100 ENOENT ⇒ empty graph, per-line `{type: "entity"|"relation"}` dispatch; `saveGraph` :102–118 join-lines rewrite; `createEntities` :120–127 name-dedupe; `createRelations` :129–139 triple-dedupe; `addObservations` :141–157 throws on unknown entity, content-dedupes; `deleteEntities` :159–164 cascades to relations touching deleted names; `deleteObservations`/`deleteRelations` :166+ tolerate missing targets; env-path migration `ensureMemoryFilePath` :15–45 memory.json→memory.jsonl); tool registrations at :276+.

**Signature:** `class KnowledgeGraphManager { loadGraph(): Promise<KnowledgeGraph>; saveGraph(g): Promise<void>; createEntities(...): Promise<Entity[]> /* only the NEW ones */ }`.

### Decisive source
```ts
// src/memory/index.ts:120-127 + 159-164 — idempotence + cascade, verbatim:
const newEntities = entities.filter(e =>
  !graph.entities.some(existingEntity => existingEntity.name === e.name));
graph.entities.push(...newEntities);
await this.saveGraph(graph);
return newEntities;          // callers see exactly what changed
...
async deleteEntities(entityNames: string[]): Promise<void> {
  const graph = await this.loadGraph();
  graph.entities = graph.entities.filter(e => !entityNames.includes(e.name));
  // Referential integrity: relations anchored on deleted entities die too.
  graph.relations = graph.relations.filter(r =>
    !entityNames.includes(r.from) && !entityNames.includes(r.to));
  await this.saveGraph(graph);
}
```
Storage shape: one JSON object per line (`{type:"entity", name, entityType, observations[]}` / `{type:"relation", from, to, relationType}`) in a flat file whose path comes from `MEMORY_FILE_PATH` (absolute) or migrates legacy `memory.json` → `memory.jsonl` at startup (:15–45). `searchNodes` is substring-match over name/type/observations plus one hop of related entities. Every mutation follows load→mutate-in-memory→save-whole-file; concurrent writers are out of scope by design (single-user local server).

**Flow:** each tool call re-reads the file (no long-lived cache) → applies SET semantics (creates return only newly-added items; duplicate observations filtered by string equality; missing-entity observation adds throw while deletes silently no-op) → rewrites all lines. This gives crash-consistent simple state with human-inspectable diffs (git-friendly).

**Invariant:** create operations are IDEMPOTENT under retry (dedupe before push, return the delta), delete of an entity invalidates its relations in the same write, and unknown-target DELETES are no-ops while unknown-target ADDS throw — porters who invert these break LLM retry loops that naturally re-issue identical calls.

**Probe:** `src/memory/__tests__/knowledge-graph.test.ts` (518L) drives `KnowledgeGraphManager` directly against a temp JSONL file (beforeEach mints `test-memory-${Date.now()}.jsonl`, afterEach unlinks) — pins the exact contracts: createEntities returns only the NEW entities (`:44–56` "should not create duplicate entities" ⇒ length 0 on re-create), addObservations THROWS on unknown entity (`:148–155`), deleteEntities cascades relations (`:171–188` "should cascade delete relations when deleting entities"), deleteObservations/deleteRelations tolerate missing targets (`:197–221`), searchNodes is case-insensitive substring over name/type/observations with one-hop relation inclusion (`:281–327`), openNodes pulls all relations connected to the open set (`:342–390`). Graph anchors: hotspots list `loadGraph` fan_in 9 / `saveGraph` fan_in 6 (get_architecture), TESTS edges from search_graph. Coverage caveat: run the vitest suite from a full checkout (published-layout clones lack node_modules).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "KnowledgeGraphManager loadGraph saveGraph createEntities deleteEntities jsonl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt set-semantics mutations returning deltas, cascade-on-delete referential integrity, lenient-delete/stict-add error asymmetry, and line-delimited self-typed records for a zero-dependency knowledge store; adapt storage to SQLite/your backend for concurrency and scale; omit the naive substring search once your corpus exceeds trivial size.
