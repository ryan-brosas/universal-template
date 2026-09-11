<!-- capsule-v2 -->
# mem0-style fact-list summary boundary — how do you reuse a memory library's reconciliation prompt without its 12 MB dependency tree?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How should an LLM-extracted fact list be built lazily, bound to speaker identity, and reconciled against hallucinated edit events?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/db/summaries.py` — `_FACT_EXTRACTION_PROMPT` (:27-48), `_build_identity_binding` (:51-63), `extract_facts` (:90-121), `materialize_profile_summary_if_missing` (:126-164), `reconcile_facts`/`_request_memory_actions`/`_parse_memory_response`/`_apply_memory_actions` (:183-258).
**Signature:** `extract_facts(text, *, seller_name: str, context: str = "") -> list[str]`; `reconcile_facts(existing: list[str], new_facts: list[str], *, seller_name) -> list[str]`.
**Data Shape:** facts stored as `Deal.profile_summary = {"facts": [...]}` — a campaign-scoped derived cache (delete + re-run rebuilds it from the lead's stored `profile_text`, no re-scrape). Reconcile events are `{id, text, event ∈ ADD|UPDATE|DELETE|NONE}`.

### Decisive source
```python
# Vendored fact-extraction prompt — modeled on mem0's FACT_RETRIEVAL_PROMPT.
# Kept inline so we don't pull mem0ai's transitive deps (qdrant, grpcio,
# sqlalchemy, posthog, ~12 MB) just for one constant string.
_FACT_EXTRACTION_PROMPT = """..."""

def _apply_memory_actions(existing, actions):
    for action in actions:
        if not action.text:
            continue
        if action.event == "ADD":
            store[str(next_id)] = action.text; next_id += 1
        elif action.event == "UPDATE":
            if action.id in store: store[action.id] = action.text
            else: logger.warning("UPDATE skipped: unknown id %r", action.id)
        elif action.event == "DELETE":
            if store.pop(action.id, None) is None:
                logger.warning("DELETE skipped: unknown id %r", action.id)
```

**Flow:** first follow-up touch → lazy materialize (no-op if built; warn-and-skip if the lead has no profile_text) → extract with temperature 0 / timeout 60 → persist. The reconcile twin mirrors mem0 upstream `c239d8a4 :594-700` with two substitutions: vector-store ops → in-memory dict keyed by index; mem0's LLM call → pydantic-ai `run_agent_sync`. Raw-text responses route through vendored `remove_code_blocks` → `json.loads` → `extract_json` fallback so markdown fences and `<think>` blocks parse cleanly.
**Invariant:** Speaker identity is *bound into the prompt*: `[Me] is named {seller_name}`, because a `[Lead]` message greeting the seller by name ("Hola Diego, gracias...") otherwise becomes a false fact about the lead — the tags carry no name binding on their own. Hallucinated ids are logged-and-skipped, never crashes; empty new-facts short-circuits without an LLM call.
**Probe:** `tests/db/test_summaries.py` — TestMaterializeProfileSummary ×3 (:83-123), TestReconcileFacts ×7 (:134-244) incl. contradiction-DELETE+ADD, in-place UPDATE, unknown-id skip with caplog assert, NONE no-op, fenced JSON, and `<think>` stripping; extraction asserts the rendered system prompt contains `"[Me] is named Diego"` (:79).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "extract_facts reconcile memory actions summary", limit: 10 });
```

## Verdict
Adopt: vendor the single prompt constant instead of the dependency; lazy derived-cache materialization; explicit speaker-name binding for any [Me]/[Lead]-tagged transcript; tolerant ADD/UPDATE/DELETE/NONE application over an id-keyed dict. Adapt storage to your row shape; omit the pydantic-ai Agent wiring.
