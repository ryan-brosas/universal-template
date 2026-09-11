<!-- capsule-v2 -->
# Additive-only schema bootstrap — CREATE TABLE IF NOT EXISTS + information_schema-guarded ALTERs as the migration plane

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How does an embeddable engine own its schema without clobbering deployments that already have richer tables?

## initializeDatabase bootstrap pattern
**Path/Symbol:** `src/lib/database.ts:initializeDatabase` (:42-615): tables :66-214, column guards :222-556, indexes :558-593; retry helper `connectWithRetry` (:21-39).
**Signature:** `async function initializeDatabase(options?: { url?: string; pool?: { min?; max? } }): Promise<void>` — assigns module-level `db = new Pool(...)`.
**Data Shape:** Every optional column added via one DO-block shape: `IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=... AND column_name=...) THEN ALTER TABLE ... ADD COLUMN ... END IF`; renames guarded BOTH directions (`IF EXISTS old AND NOT EXISTS new THEN RENAME`).

### Decisive source
```sql
-- database.ts:54-65 — WHY core creates a table it doesn't really own:
-- The redirect path LEFT JOINs this table to read `settings.appConfig` ...
-- Core therefore *depends* on the table existing even though richer
-- deployments own the real one ... Deliberately minimal — id and settings are
-- all the redirect reads ... CREATE TABLE IF NOT EXISTS is a no-op against a
-- deployment that already ships a fuller organizations table, so this cannot clobber one.
CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  settings JSONB DEFAULT '{}',
  suspended_at TIMESTAMP, ...);
```

**Flow:** pool with prod SSL `{ rejectUnauthorized: false }` → connectWithRetry retries ONLY ECONNREFUSED up to 10× exponential backoff (1s base), rethrowing anything else → tables in dependency order (organizations/link_templates BEFORE links FK) → additive columns (warn_at/disabled_at/disabled_reason, attribution columns, sdk identity, last-click stamps) → indexes incl. partial ones (`WHERE is_bot = false`, `WHERE session_id IS NOT NULL`) → client released in finally.
**Invariant:** All evolution must be additive + guarded (no destructive DDL); minimal seed tables must be no-op-safe against fuller deployed versions; deferred index decisions documented until a real consumer exists (sdk_name note :537-539); every new column needs a default or NULLability so existing rows behave as-before.
**Probe:** `bash -c "grep -c 'information_schema.columns' src/lib/database.ts"` → 34 (guarded ALTER blocks + rename shims; count LINES); `bash -c "grep -cF 'information_schema.columns' src/lib/link-safety.ts"` → 1 (the runtime probe); direct tests: none execute DDL (needs live PG) — recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "information_schema.columns guarded ALTER database bootstrap", limit: 10, fields: ["signature", "name", "file"] });
```
*Retrieve drift note (2026-08-24 pass-2 liveness battery):* the original query `initializeDatabase CREATE TABLE IF NOT EXISTS organizations` returns total:0 — BM25 AND-semantics: body-comment tokens (`CREATE TABLE IF NOT EXISTS`) don't index on Function nodes, and `CREATE`/`TABLE` are stop-words, so only `initializeDatabase` carries weight and ANDing kills it. The shipped query live-resolves rank-1 line-exact (`initializeDatabase` :42-615).

## Verdict
Adopt guarded-additive bootstrap for any library that ships schema; adapt table set; omit the rename shims once your version floor guarantees the new names — keep partial indexes matched to real query shapes either way.
