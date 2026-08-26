<!-- capsule-v2 -->
# generated-column-countall-multivalue — How does COUNTALL count elements of a jsonb multi-value column in an immutable generated column?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What exact SQL counts json array elements (vs scalar 0/1), and how is jsonb-null handled?

## jsonb_typeof='array' → jsonb_array_length; NULLIF against 'null'::jsonb; scalar → CASE 0/1
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/generated-column-query/postgres/generated-column-query.postgres.ts:countAll` (:1420-1445, key lines :1429-1431).
**Signature:** `countAll(valueExpr: string): string` under setCallMetadata with the field's slot info.
**Data Shape:** normalized = NULLIF((x)::jsonb, 'null'::jsonb); output integer.

### Decisive source
```ts
WHEN jsonb_typeof(${normalized}) = 'array' THEN jsonb_array_length(${normalized})
```
with upstream direct spec pinning both arms:
```ts
const sql = query.countAll('"__owners"');
expect(sql).toContain('jsonb_array_length');
expect(sql).toContain(`NULLIF(("__owners")::jsonb, 'null'::jsonb)`);
...
expect(query.countAll('"__number"')).toBe('CASE WHEN "__number" IS NULL THEN 0 ELSE 1 END');
```

**Flow:** metadata says multi-value json → cast to jsonb → strip jsonb null → array? count elements : scalar 0/1 CASE. Immutable throughout — no subqueries needed.
**Invariant:** `NULLIF(x::jsonb,'null'::jsonb)` exists because jsonb stores SQL NULL ambiguously after casts; without it jsonb_array_length('null') raises. The scalar arm is byte-stable (`toBe`) — a porter changing its shape breaks the spec.
**Probe:** upstream direct spec `generated-column-query.postgres.spec.ts:36-63` (both polarities quoted above); static byte-exact: `grep -n "NULLIF((\${normalized})" generated-column-query.postgres.ts | head -2`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"countAll","limit":5,"detail":"ids"}'
```

## Verdict
Adopt both arms + null-strip. Adapt type names. Omit nothing.
