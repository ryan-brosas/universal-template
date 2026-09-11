<!-- capsule-v2 -->
# Audit turn mining — how do you record one chat row plus its artifact rows without ever breaking the chat?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How does an audit trail capture LLM-turn artifacts (generated/edited/replicated docs, applied workflows) when the source of truth is a heterogeneous SSE event stream, and auditing must never throw into the user-facing path?

## Fire-and-forget inserts + event-shape-aware mining
**Path/Symbol:** `backend/src/lib/audit.ts:26` (`recordAudit`), `:69` (`recordChatTurn`). Direct test: `backend/src/lib/__tests__/audit.test.ts`.
**Signature:** `recordAudit(db, AuditEventInput) -> Promise<void>` (never rejects); `recordChatTurn(db, base, events) -> Promise<void>`.
**Data Shape:** `AuditEventInput{userId,userEmail?,action,status?,title?,surface?,projectId?,chatId?,documentId?,reviewId?,model?,detail?}`; status ∈ completed|cancelled|failed; `title` clamped `.slice(0,300)`.

### Decisive source
```ts
try {
  const { error } = await db.from("audit_events").insert({ ... });
  if (error) console.error("[audit] insert failed:", error.message); // Supabase reports in-band
} catch (err) { console.error("[audit] insert threw:", ...); }        // transport failure swallowed
```

**Flow:** one `chat.message` row per turn (surface = projectId ? "project" : "assistant"; detail only when flags non-empty) → then iterate the turn's assistant events mapping type→action: doc_created→document.generated, doc_edited→document.edited, workflow_applied→workflow.applied (+`detail.workflow_id`) → **doc_replicated is special: it fans out to one document.generated row PER COPY**, reading the copy's own `new_filename`/`document_id`, never the source's top-level filename (the top-level `filename` is the SOURCE; there is no top-level document_id).
**Invariant:** Audit failures are logged and swallowed by design — recording must NEVER throw or block the user-facing path. Empty-copies replication emits zero artifact rows. Unknown event types are skipped silently (`if (!action) continue`).
**Probe:** `grep -c 'it(' src/lib/__tests__/audit.test.ts` → 3 incl "mines doc_replicated from its copies, not the source filename/id" and "emits no artifact rows for a doc_replicated with empty copies".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "recordAudit recordChatTurn audit event", limit: 10 });
```

## Verdict
Adopt never-throw audit wrappers + in-band error handling for builders that report instead of reject + per-copy fan-out mining from event streams; adapt the action vocabulary and clamps to your schema; omit the specific event-type union.
