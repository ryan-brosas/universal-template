<!-- capsule-v2 -->
# Audit scratchpad DO — where does a site-audit crawler keep frontier/link state when Workflow step outputs cap at ~1MiB?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** What is the DO's table layout, write discipline, and cleanup guarantee?

## SQLite-in-Durable-Object crawl scratchpad
**Path/Symbol:** `src/server/features/audit/AuditScratchpad.ts:AuditScratchpad` (:86-123 schema + lifecycle; full class :1-377).
**Signature:** `class AuditScratchpad extends DurableObject` — RPCs: `seedStart(url)`, `seedSitemapUrls(urls)` (2,000/RPC batch), `claimNextUrls`, `recordBatch({crawledUrls, pages, links, discovered})`, `runFinalizeChecks({startUrl, crawlCompleted})`, `destroy()`.
**Data Shape:** Three tables: `frontier(url PK, depth, source, in_sitemap, state, chunk_no)`, `links(source_page_id, target_url PK pair, anchor, is_nofollow)`, `page_mirror(page_id PK, url UNIQUE, status_code, fetch_class, redirect_url)`. Budgets: `LINK_STORAGE_BUDGET_BYTES=500MB` (link rows are the only unbounded-per-page data; past budget the crawl continues minus link-graph issues — protects the 1GB per-object SQLite cap), `BROKEN_LINK_ISSUE_CAP=2000`.

### Decisive source
```ts
// Guarantee the cleanup alarm on EVERY instantiation, not just at seed:
// any RPC (even one racing in right after destroy()) re-creates the
// tables above, and without an alarm that storage would leak forever.
void this.ctx.blockConcurrencyWhile(() => this.ensureCleanupAlarm());
```

**Flow:** discovery seeds the frontier (seeds go straight into the DO — nothing large returns as step state; an uncapped seed list used to blow the ~1MiB step-output limit on big sitemaps) → each crawl chunk claims URLs, records results idempotently (every insert OR IGNORE/OR REPLACE on stable keys because workflow steps retry), discovers same-origin links → finalize runs broken-link/orphan SQL locally in the DO → destroy on success. Self-cleanup alarm set at 7 days (`CLEANUP_AFTER_MS`) wipes any instantiation, including races after destroy; failed audits' state doubles as resume/debug artifact until then.
**Invariant:** All methods are synchronous inside (SQLite in DOs is sync) so each RPC is effectively atomic. The alarm must be re-armed in the CONSTRUCTOR, not at seed time. Orphan detection only makes sense when the crawl wasn't truncated (`crawlCompleted` flag).
**Probe:** `grep -n "ensureCleanupAlarm\|blockConcurrencyWhile" src/server/features/audit/AuditScratchpad.ts` (constructor re-arm pinned); behavior via `src/server/workflows/siteAuditWorkflowPhases.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "AuditScratchpad frontier seedSitemapUrls LINK_STORAGE_BUDGET", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the DO/scratchpad pattern (chatty crawl writes off the main DB, no step-output limits, local SQL for finalize checks) for any bounded crawler on durable-execution platforms. Adapt to your platform's equivalent of DOs+sync SQLite. Omit the link-budget mechanism only if you have unbounded storage.
