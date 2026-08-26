<!-- capsule-v2 -->
# Tool-invocation identity dedup gate — when does a repeated tool call_id fail loud vs dedupe silent?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** Before any sibling tool executes, how are one response's tool invocations validated for call-id reuse across history and within the same response?

## Identity preflight over all run kinds
**Path/Symbol:** `src/agents/run_internal/tool_planning.py:` `_dedupe_processed_response_invocations` (:339–554), `_preflight_mcp_approval_requests` (:199–224), `should_keep` inner gate (:399–486), reasoning-drop tail (:538–553).
**Signature:** `def _dedupe_processed_response_invocations(processed_response, *, context_wrapper, existing_items, deferred_binding_validation_raw_item_ids=None, filter_completed=True) -> set[int]`.
**Data Shape:** invocation identity = `(type, call_id, fingerprint)` via `tool_invocation_identity`; output keys = `(raw_type, call_id)` from completed `ToolCallOutputItem`s; skipped items tracked by `id(raw_item)`.

### Decisive source
```python
if identity[1] in uncanonical_response_call_ids:
    raise ModelBehaviorError("Model reused a tool call ID for a different invocation ...")
historical_identity = completed_historical_invocations.get(identity[1])
if historical_identity is not None:
    if historical_identity != identity:
        raise ModelBehaviorError("Model reused a completed tool call ID ...")
    if filter_completed:
        skipped_raw_item_ids.add(id(raw_item)); return False   # exact repeat ⇒ drop silently
previous_identity = current_response_invocations.get(identity[1])
if previous_identity is not None:
    if previous_identity != identity:
        raise ModelBehaviorError(...)
    skipped_raw_item_ids.add(id(raw_item)); return False       # dup within one response ⇒ drop
```
Legacy bridge: when allowed, a nameless ToolCallItem can reconstruct its identity from the recorded legacy invocation so old histories don't false-positive. A binding-validation `ModelBehaviorError` is SWALLOWED only when an exact completed sibling with the same provider id predates approval binding ("preserve released cross-kind resume behavior"); changed content still fails closed. Executed-but-uncommitted status (`binding_status[2] and not [1]`) raises "Start a new run instead of retrying."

**Flow:** build completed-output key set + historical identity map from existing items → MCP preflight (same-ID siblings with DIFFERENT content raise; exact duplicates coalesce by raw-item id) → filter every plan bucket through `should_keep` → dropped calls take their tied REASONING items with them (same next-non-reasoning association grammar as the retention rules).

**Invariant:** Same id + different content = model bug ⇒ ALWAYS loud (history, one-response, or MCP-sibling scope); same id + same content = replay ⇒ silently filtered exactly once per scope; validation completes BEFORE any user callback or sibling tool starts.

**Probe:** `tests/test_tool_approval_call_id_reuse.py` (:80–164 pins canonical identity edge cases incl. stripped metadata and null-preserving fingerprints).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "dedupe processed response invocations tool call id reuse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt identity-scoped dedup with loud-mismatch semantics for any executor that resumes after interruptions; adapt the identity tuple to what your provider guarantees unique; omit the legacy reconstruction lane if you have no historical format migration.
