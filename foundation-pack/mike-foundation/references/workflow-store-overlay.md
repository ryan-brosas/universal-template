<!-- capsule-v2 -->
# Workflow store overlay — how do catalog workflows coexist with user workflows without crashing the chat?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do you merge a global content-addressed workflow catalog, user-owned workflows, and email-shared workflows into one Map with correct visibility — and survive every lookup failing?

## Three-source overlay with listed:false catalog + best-effort defaults
**Path/Symbol:** `backend/src/lib/chat/contextBuilders.ts:754` (`buildWorkflowStore`); helpers `src/lib/workflowCatalog.ts:160` (`ensureDefaultWorkflows`), `catalogWorkflowId`. Direct test: `src/lib/__tests__/workflowCatalog.test.ts` (suite green at pin).
**Signature:** `buildWorkflowStore(userId, userEmail, db) -> WorkflowStore` (Map id → `{title, skill_md, listed?, reference_files?}`).
**Data Shape:** catalog ids are readable slugs (`catalogWorkflowId(workflow_key)`) kept for historical chat attachments but `listed:false` (hidden from list_workflows); user + shared entries `listed:true`; active versions sort first, inactive content-addressed versions remain as fallback.

### Decisive source
```ts
// Best-effort: the chat routes call this OUTSIDE their try blocks, so a thrown
// error here becomes an unhandled rejection that kills the process (Express 4
// does not forward async errors). A chat must never fail — let alone crash the
// backend — because default installation failed.
try { await ensureDefaultWorkflows(userId, db); }
catch (err) { console.error("[buildWorkflowStore] ensureDefaultWorkflows failed:", err); }
if (store.has(id) || !workflow.prompt_md) continue;   // first-wins; empty bodies skipped
```

**Flow:** ensure defaults (swallowed) → catalog query ordered active-first/updated-desc → user-owned `workflows` overlay → `workflow_shares` by normalized email → dedupe via `store.has(id)` → batch-fetch `workflow_reference_documents` for all LISTED ids and attach reference files onto their workflow entries.
**Invariant:** The function must never throw (caller's try-block boundary is above it). Catalog entries must remain RESOLABLE (old chats reference them) while staying unlisted; user rows shadow catalog ids only when the catalog hasn't already claimed the slug.
**Probe:** `grep -c 'it(' src/lib/__tests__/workflowCatalog.test.ts | head -1`; targeted: `grep -c "ensureDefaultWorkflows" src/lib/chat/contextBuilders.ts` → 2 (call + log tag).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "buildWorkflowStore ensureDefaultWorkflows catalog overlay", limit: 10 });
```

## Verdict
Adopt never-throw store construction + listed/unlisted dual-visibility + first-wins overlay order; adapt id schemes and share mechanics to your schema.
