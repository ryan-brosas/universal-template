<!-- capsule-v2 -->
# Logs SQL rewrite offer gate — when should a UI offer to rewrite a user's SQL for a new backend dialect, and how do you detect the old dialect without a parser?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A project's logs moved from BigQuery to ClickHouse; existing saved queries are BigQuery-dialect. What exact conditions must hold before offering an AI rewrite, how is legacy dialect detected on raw text, and what request shape hands the query to the completion route?

## Dialect sniffing + source detection (`data/logs/logs-sql-rewrite.ts`)
**Path/Symbol:** `apps/studio/data/logs/logs-sql-rewrite.ts` : `looksLikeLegacyLogsQuery` (:30-36), `detectLogSource` (:13-28), `SOURCE_ALIASES` (:9-11), `LEGACY_LOGS_DIALECT_CHECK_DEBOUNCE_MS` (:42), `shouldOfferLegacyLogsRewrite` (:50-58), `stripSqlCodeFences` (:3-7).
**Signature:** `shouldOfferLegacyLogsRewrite({ sql, isClickhouseLogsEnabled }): boolean`; `detectLogSource(sql): string | undefined`; `looksLikeLegacyLogsQuery(sql): boolean`.
**Data Shape:** three regex heuristics, no parser: legacy iff `unnest(` appears OR `cast(timestamp as datetime)` appears OR the FROM table name is not `logs`. Source detection reads `\bsource\s*=\s*'([^']+)'` — the word boundary is load-bearing so lookalike columns (`resource = '…'`, `datasource = '…'`) never match — then falls back to the FROM table name; `SOURCE_ALIASES` maps `pg_cron_logs` → `postgres_logs`; the bare `logs` table yields `undefined` (no specific source).

### Decisive source
```ts
export function looksLikeLegacyLogsQuery(sql: string): boolean {
  const lower = sql.toLowerCase()
  if (/\bunnest\s*\(/.test(lower)) return true
  if (/cast\s*\(\s*timestamp\s+as\s+datetime\s*\)/.test(lower)) return true
  const byFrom = lower.match(/\bfrom\s+([a-z_][a-z0-9_]*)/)
  return byFrom ? byFrom[1] !== 'logs' : false
}

/**
 * Whether to offer the ClickHouse rewrite for a query. Both the flag and the
 * dialect check matter: on an org whose logs haven't moved to ClickHouse the
 * BigQuery text is still *correct*, so offering to rewrite it would break a
 * working query. Callers layer their own dismissal state on top.
 */
export function shouldOfferLegacyLogsRewrite({ sql, isClickhouseLogsEnabled }) {
  return isClickhouseLogsEnabled && looksLikeLegacyLogsQuery(sql)
}
```

**Flow:** editor text settles for 500ms (shared debounce constant so every surface reacts on the same cadence) → dialect check runs → offer shown only when BOTH the org-level migration flag AND the legacy-dialect heuristic hold → caller layers its own dismissal state on top.
**Invariant:** the offer gate is a conjunction of a per-org capability flag and a per-query dialect check. Dropping either half either breaks working queries (offering on non-migrated orgs) or nags on already-migrated text. Heuristic detection must be conservative: false negatives just mean no offer, false positives rewrite correct SQL.
**Probe:** `apps/studio/data/logs/logs-sql-rewrite.test.ts` (pure vitest, read whole; unexecutable in-lane — standing block) pins: offer tri-state (legacy+flag ⇒ true, flag off ⇒ false, ClickHouse/empty ⇒ false); `resource =`/`datasource =` lookalikes rejected while qualified `t.source =` still matches and a real `source` column wins over an earlier lookalike; `pg_cron_logs` alias from both FROM and filter positions; unnest/cast idioms flagged; bare `logs` table not flagged.

## AI rewrite request contract
**Path/Symbol:** same file : `rewriteLogsSqlWithAI` (:76-113), `RewriteLogsSqlArgs` (:60-67).
**Signature:** `rewriteLogsSqlWithAI({ sql, projectRef, connectionString?, orgSlug?, authorizationHeader?, availableKeys? }): Promise<string>`.
**Data Shape:** POST `${BASE_PATH}/api/ai/code/complete` with `{ projectRef, connectionString, language:'sql', dialect:'clickhouse', intent:'rewrite', orgSlug, completionMetadata: { textBeforeCursor:'', textAfterCursor:'', prompt:'', selection: sql, availableKeys } }`. The whole query is the SELECTION and the prompt is empty — the instruction for the `rewrite` intent lives server-side (`lib/ai/clickhouse-logs.ts`), so exactly one place knows how a completion prompt is assembled. Response: non-ok ⇒ throw the error text; body passes through `stripSqlCodeFences` (```sql or plain fenced block, prose-wrapped tolerated); empty result ⇒ throw `'The assistant returned an empty query'`.

### Decisive source
```ts
completionMetadata: {
  // The whole query is the selection, so the rewrite replaces all of it and
  // the route supplies the instruction for the `rewrite` intent.
  textBeforeCursor: '',
  textAfterCursor: '',
  prompt: '',
  selection: sql,
  availableKeys,
},
// ...
const raw = await response.json()
const rewritten = stripSqlCodeFences(typeof raw === 'string' ? raw : String(raw))
if (!rewritten) throw new Error('The assistant returned an empty query')
```

**Flow:** declare intent + hand over the selection → server assembles the prompt → model returns possibly-fenced text → fence-strip → empty-guard → return clean SQL for the caller to apply behind its own confirmation.
**Invariant:** client-side carries NO prompt text for intent-driven rewrites — the route owns the instruction, keeping prompt assembly in one place across inline edits and whole-query rewrites. Model output is hostile input: always fence-strip and always guard against empty before it touches the editor.
**Probe:** same test file pins the exact request shape (dialect clickhouse, intent rewrite, selection = whole query, empty prompt/before/after, availableKeys passthrough), the failure throw (`'boom'`), and the empty-model-output throw.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct whole-file reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "shouldOfferLegacyLogsRewrite looksLikeLegacyLogsQuery rewriteLogsSqlWithAI detectLogSource", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the conjunction offer gate (capability flag ∧ conservative dialect heuristic), the word-boundary source-column detection with alias table, the shared debounce constant, and the intent-declaring request shape where the server owns the prompt and the client fence-strips + empty-guards model output. Adapt the heuristic set to your old/new dialect pair (each idiom must be something the new dialect cannot contain) and the endpoint to your completion route. Omit Supabase's org-migration flag semantics if your deployment migrates atomically — then only the dialect check remains. Caveat: heuristics are text-level; a query that mixes dialects is out of scope by design.
