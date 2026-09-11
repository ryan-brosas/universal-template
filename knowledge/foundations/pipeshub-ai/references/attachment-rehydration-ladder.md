<!-- capsule-v2 -->
# Attachment rehydration ladder — how do attachments survive across HTTP requests when every run builds a fresh in-memory agent?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** citation maps and record caches are process-local, but conversations span requests — how does turn-0 restore them without the model re-uploading files?

## Three entry points, one read-only blob contract
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/attachment_resolver.py` — `resolve_attachments_for_goal` :60-143 (factory, before run), `attachment_rehydration` :171-233 (PRE_TURN, turn 0 only), `resolve_history_attachments` :366-459 (history seeding), `_register_fetch_tool` :310-339.
**Signature:** `attachment_rehydration(context) -> Middleware[TurnContext]`; `resolve_history_attachments(attachments, blob_store, org_id, ref_mapper, vrmap, *, is_multimodal_llm=False, image_budget=None) -> tuple[str, list[dict]]`.
**Data Shape:** `previous_conversations: list[dict]` with `role=="user_query"` turns carrying `attachments[].virtualRecordId`; populates `tool_state["citation_ref_mapper"]`, `["virtual_record_id_to_result"]`; returns `(text_for_goal, image_blocks)`.

### Decisive source
```python
async def _middleware(ctx: "TurnContext", next_fn: "Next") -> None:
    if ctx.turn_index != 0 or ctx.scope is None:
        await next_fn()
        return
    ...
    record_ids = await _rehydrate_citation_maps(context, historical, blob_store)
    if record_ids:
        _register_fetch_tool(ctx, context)
    goal = ctx.scope.run.goal
    ...
    if record_ids:
        ids_str = ", ".join(f'"{rid}"' for rid in record_ids)
        goal.constraints.append(
            f"User previously attached file(s): {', '.join(names)}. "
            f"Call knowledgegraph__fetch_record(record_ids=[{ids_str}]) "
            "to retrieve their full content. ")
```

**Flow:** PRE_TURN (turn 0 only; later turns see identical history so re-scanning is pure waste) → collect historical attachment refs → per-vrid blob fetch, skip-if-already-in-map → populate both citation maps as side effects → if anything resolved, early-register fetch tool + patch `run_scope.visible_tools` (a tool registered AFTER the PRE_AGENT preload snapshot stays invisible without this) → append a goal.constraints reminder teaching the model the exact call syntax.
**Invariant:** resolution is READ-ONLY against blob storage (upload API already persisted records); failure of one attachment is warn-and-continue, never fail-the-turn; even total failure appends an honest "content could not be loaded" constraint rather than silence. The image budget instance must be SHARED (`context.tool_state["image_budget"]`) so historical images count against the same conversation-wide cap.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_attachment_resolver.py` — 39 tests incl. `TestResolveAttachmentsForGoal.test_populates_citation_maps` :206. Execute: `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_attachment_resolver.py -q` (39 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "attachment_rehydration rehydrate citation maps virtual_record_id_to_result", limit: 4, fields: ["signature", "name", "file"] });
// resolves _rehydrate_citation_maps Function attachment_resolver.py 255-307 rank#1 + attachment_rehydration 171-233 rank#3
```

## Verdict
Adopt the turn-0-only rehydration pattern for any cross-request state that lives in process-local maps (citation state, tool grants, visible-tool sets): scan history, refill from durable store, patch post-snapshot visibility sets, and tell the model in constraints what it can now do. Adapt storage backend and reminder wording. Omit PipesHub virtualRecordId/blob-store plumbing.
