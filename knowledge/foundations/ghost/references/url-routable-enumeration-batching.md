<!-- capsule-v2 -->
# Routable enumeration batching — how do you list every routable row without loading the table or tripping driver limits?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory project `ghost`. **Question:** What is the on-demand replacement for a boot-time URL cache when a consumer needs ALL routable resources of a type (sitemap, search index, exports)?

## fetchRoutableResources
**Path/Symbol:** `ghost/core/core/server/services/url/routable-resources.js:fetchRoutableResources` (:56–118), `TYPE_CONFIG` (:17–37), `RELATION_FIELDS` (:39–42), `SQLITE_BATCH_SIZE` (:45); requirements supplied by `LazyUrlService.getRoutableResources` (:345–354).
**Signature:** `async fetchRoutableResources(type, { columns = [], requiredFields = [], requiredRelations = [] } = {}): Promise<Object[]>`.
**Data Shape:** `TYPE_CONFIG[type] = { modelName, table, filter, canCarryRelations?, shouldHavePosts?: {joinTo, joinTable} }`; tags/authors carry `shouldHavePosts` joins to `posts_tags.tag_id` / `posts_authors.author_id`.

### Decisive source
```js
// Callers speak include; raw_knex only speaks exclude, so translate
// against the table schema here, once.
const include = new Set(['id', ...columns, ...requiredFields]);
const options = { modelName, filter,
  exclude: Object.keys(schema.tables[typeConfig.table]).filter((column) => !include.has(column)) };
...
let batch;
do {
  // orderBy makes the pagination deterministic; without it the
  // row order between batches is unspecified.
  batch = await models.Base.Model.raw_knex.fetchAll({ ...options, orderBy: 'id', offset, limit: SQLITE_BATCH_SIZE });
  rows.push(...batch);
  offset += SQLITE_BATCH_SIZE;
} while (batch.length);
```
**Flow:** unknown type ⇒ IncorrectUsageError → compute exclude list = full table schema minus (id ∪ caller columns ∪ router-required fields) → relations only for types that CAN carry them AND only when the active routing config reads them, each pinned via withRelatedFields to `[<rel>.id, <rel>.slug]` → non-SQLite: single fetchAll; SQLite: offset batches of 999 ordered by id until an empty batch.
**Invariant:** "visibility:public alone is not enough for tags and authors" — without the has-posts join, empty tags and staff accounts would be routable/listable. The rows are never thin for URL computation because the service itself names requiredFields/requiredRelations from the live routing config. Models/schema are required INSIDE the function so the module's shape loads without the model layer. Batch size exists because of SQLite's bound-variable limit (#5810); determinism requires orderBy.
**Probe:** `ghost/core/test/unit/server/services/url/routable-resources.test.js` pins `"applies the routing gates for each type"` (asserts both shouldHavePosts joins), `"selects only id, the requested columns and what the routers require"` (mobiledoc/lexical/html/plaintext/title excluded), `"batches on SQLite to avoid the bound-variable limit, in a deterministic order"` (offset 0→999, limit 999, orderBy id).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ghost", query: "fetchRoutableResources SQLite batch routable", limit: 10 });
// observed at pin: fetchRoutableResources rank #1 (routable-resources.js:56-118),
// FetchRoutableResources injectable type rank #2 — email-service batch helpers are unrelated noise
```

## Verdict
Adopt include-to-exclude translation against live schema, per-relation column pinning, conditional relation loading driven by routing config, and driver-limit batching with deterministic ordering. Adapt the join-gate concept to your taxonomy tables; omit Ghost's raw_knex specifics by targeting your repository's bulk-select primitive.
