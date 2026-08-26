<!-- capsule-v2 -->
# Immutable source guard — how do library templates get protected from in-place edits while staying readable?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** What enforces "copy before edit" for templates and workflow assets, and what do the model and the user both see when it fires?

## source_kind veto + replicate-first steering + UI-shaped failure
**Path/Symbol:** `backend/src/lib/chat/tools/toolDispatcher.ts:73` (`sourceMaterialNotice`), `:1369-1404` (edit_document veto), `:1551-1565` (replicate gating); marker on DocStore entries (`types.ts:28`). Direct tests: `src/lib/__tests__/workflowAssetReplication.test.ts`, integration `src/__tests__/integration/workflowAddons.routes.test.ts`.
**Signature:** veto condition: `docInfo?.source_kind === "library_template" || === "workflow_asset"`; replicate requires `new_filename` when source is immutable.
**Data Shape:** failures emit a REAL event pair (doc_edited_start → doc_edited with `error` field, empty version/url) so the UI renders a failed "Edited" block matching the success/late-failure shape.

### Decisive source
```ts
const err = "Templates and workflow assets cannot be edited directly. Call replicate_document with a new_filename, then edit the returned copy.";
emitEditError(docInfo.filename, indexed?.document_id ?? "", err);
toolResults.push({ role: "tool", tool_call_id: tc.id,
    content: JSON.stringify({ error: err }) });       // model gets the SAME steer
```

**Flow:** read_document attaches a `sourceMaterialNotice` line ("immutable; call replicate_document… reading it for information needs no copy") so the model learns the rule BEFORE attempting an edit → edit_document on an immutable source fails fast with the steer → replicate_document REQUIRES new_filename for immutable sources (prevents silent overwrite-style copies) and stamps copies `source_kind:"document"` so they're freely editable.
**Invariant:** The veto is identity-based (source_kind), not name/path-based. Reading is never blocked — only mutation. Both channels (SSE event + tool result) carry the same instruction so UI and model can't diverge.
**Probe:** `grep -c 'cannot be edited directly' src/lib/chat/tools/toolDispatcher.ts` → 1; `grep -c 'A new_filename is required' src/lib/chat/tools/toolDispatcher.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "library_template workflow_asset replicate_document source_kind", limit: 10 });
```

## Verdict
Adopt kind-based immutability + read-free/edit-veto + dual-channel steering as portable contracts; adapt your template taxonomy and notice copy.
