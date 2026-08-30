<!-- capsule-v2 -->
# Prisma raw-SQL param rewriting + read-replica routing — how do you keep `{{name::type}}` SQL portable across prisma/pg while sending writes to the primary?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are named params rewritten to positional $n placeholders, and how does replica routing distinguish reads from writes?

## prisma-raw-rewrite-replica
**Path/Symbol:** `src/lib/prisma.ts:executeRawQuery :717-752 (regex rewrite :731), getRawQueryClient :40-66, writeRawQuery :757-759`; direct tests `src/lib/prisma.test.ts:46-90`.
**Signature:** `sql.replaceAll(/\{\{\s*(\w+)(::\w+)?\s*}}/g, ...)` → `$N[::cast]` positional; `getRawQueryClient(client,{useReplica,write})`.
**Data Shape:** `{{websiteId::uuid}}` — name + optional Postgres cast ride along to `$1::uuid`.

### Decisive source
```ts
const query = sql?.replaceAll(/\{\{\s*(\w+)(::\w+)?\s*}}/g, (...args) => {
  const [, name, type] = args;
  const value = data[name];
  params.push(value);                    // first occurrence wins position; duplicates push again
  return `$${params.length}${type ?? ''}`;
});
const queryClient = getRawQueryClient(client, {
  useReplica: !!process.env.DATABASE_REPLICA_URL,
  write,                                 // writeRawQuery sets true ⇒ $primary()
});
```

**Flow:** template SQL with double-brace names → ordered params array → `$n` positional query → routed client (`$replica()` for reads when replicas configured, `$primary()` for ANY write). Schema search_path is set per-execute when `?schema=` is in DATABASE_URL.
**Invariant:** duplicate a named param in SQL and it pushes the value twice (positional count must stay aligned — never de-duplicate params). Write routing checks `$primary` as a FUNCTION before calling (`typeof client.$primary === 'function'`) and falls back to the base client on plain drivers.
**Probe:** `grep -c "test(" src/lib/prisma.test.ts` → 4 (:47-77 replica-read/primary-write/fallback selection exactly).
**Probe:** `grep -n "uses a replica client for read queries" src/lib/prisma.test.ts` → :47.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "executeRawQuery getRawQueryClient writeRawQuery", limit: 10 });
```

## Verdict
Adopt named→positional rewriting to keep one SQL text per dialect readable, and explicit read/write client routing over driver-level magic; adapt cast syntax to your driver; omit schema search_path if single-schema.
