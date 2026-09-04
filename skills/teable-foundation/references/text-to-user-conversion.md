<!-- capsule-v2 -->
# Text→user conversion via meta matching — how do free-text cells become user references by joining against the users table inside one UPDATE?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How are text values resolved to user records (single vs multiple) without row-by-row application round-trips?

## fetchTextUserMappings + buildTextToUserTransformSql
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/FieldTypeConversionVisitor.ts` — `fetchTextUserMappings` (:374–427), `buildTextUserPartsSql` (:365–372), `buildTextToUserTransformSql` (:428–482); avatar prefix `shared/userAvatarUrl.ts resolveUserAvatarUrlPrefix`.
**Signature:** transform builder returns SQL text or null (no mappings ⇒ no-op); executed as a custom data statement during text→user conversion.
**Data Shape:** mapping tuple `(lookupValue, id, title, email)`; output cell = `jsonb_build_object('id','title','email','avatarUrl': prefix||id)` — array-aggregated for multi-user fields (`jsonb_agg(... ORDER BY part_idx)`), first-match via `DISTINCT ON (rid) ... ORDER BY rid, part_idx` for single.

### Decisive source
```sql
WITH user_mapping(uid, id, title, email) AS (VALUES (...)),
text_parts AS (
  SELECT t.__id AS rid, parts.uid, raw_parts.part_idx::integer AS part_idx
  FROM tbl AS t
  CROSS JOIN LATERAL regexp_split_to_table(t.col, ',') WITH ORDINALITY AS raw_parts(part, part_idx)
  CROSS JOIN LATERAL (SELECT trim(raw_parts.part) AS uid) AS parts
  WHERE t.col IS NOT NULL AND parts.uid <> ''
), matched_users AS (
  SELECT p.rid, p.part_idx, u.id, u.title, u.email
  FROM text_parts p JOIN user_mapping u ON u.uid = p.uid
), aggregated AS ( ... jsonb_agg or DISTINCT ON ... )
UPDATE tbl AS t SET col = aggregated.user_json FROM aggregated WHERE t.__id = aggregated.rid;
```

**Flow:** pre-pass splits the column into distinct trimmed tokens (data plane), matches them against `users` (name/email lookup on meta plane) building an explicit VALUES map, then a single set-based UPDATE rewrites only rows whose tokens matched — unmatched text becomes NULL by omission.
**Invariant:** resolution is exact-token equality after trim/comma-split (no fuzzy matching); unmatched values silently clear; avatar URLs are rebuilt from a configured prefix at CONVERSION time, not stored relative.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/__tests__/FieldTypeConversionVisitor.pglite.spec.ts:128 'should resolve matching text via meta DB and clear non-matching text'`, :190 'should create array format for multiple user field'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildTextToUserTransformSql fetchTextUserMappings TextUserMapping", limit: 10 });
```

## Verdict
Adopt the tokenize→map→set-based-UPDATE pipeline with explicit VALUES maps and part-index-preserving aggregation; adapt the token grammar (comma split) and user identity fields to host; omit avatar-prefix handling if host stores URLs differently.
