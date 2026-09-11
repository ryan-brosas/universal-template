<!-- capsule-v2 -->
# Knowledge scope negotiation — how do you expose "all/agent/session" scopes to an LLM only when fan-out has value, and keep prompt + dispatcher in agreement?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When is the synthetic `all` scope offered, why is `session` the default, and why must two modules compute this identically?

## Scope-context ladder mirrored between tool prompt and search dispatcher
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/helpers/knowledge.py:12-49` (`_get_knowledge_tool_scope_context`, `_knowledge_scope_instruction`), twin at `src/cuga/backend/knowledge/client.py` (`KnowledgeClient.scope_context`, static).
**Signature:** `_get_knowledge_tool_scope_context(engine: Any | None, thread_id: str | None) -> tuple[tuple[str, ...], str | None]`.
**Data Shape:** Returns `(allowed_scopes, default_scope)`: both wired ⇒ `(("all","agent","session"), "session")`; one wired ⇒ `(that,)`; disabled/no-thread ⇒ `((), None)`.

### Decisive source
```python
# helpers/knowledge.py:33-40
if len(narrow_scopes) >= 2:
    # Synthetic "all" only when there's actual fan-out value.
    return ("all", *narrow_scopes), "session"
if len(narrow_scopes) == 1:
    return (narrow_scopes[0],), narrow_scopes[0]
return (), None
```
The docstring states the mirroring invariant: this helper "Mirrors `KnowledgeClient.scope_context` semantics — both must report the same shape because the same engine flags drive the LLM tool prompt (here) AND the search dispatcher in `knowledge/client.py`." Default = `session` (narrowest plausible scope; uploaded docs are almost always topical) and it's risk-free because the engine auto-falls back to `all` when session returns 0 hits. `session` requires a thread_id — no thread context ⇒ scope doesn't exist. The instruction generator emits per-configuration LLM guardrails including a distinct message for "engine configured but session impossible here" (no thread). Tool descriptions get only a short hint line (`Allowed scopes: ...`) since full rules already live in system instructions.

**Flow:** graph setup reads engine config + thread presence → scope tuple → (a) prompt instructions, (b) decorated tool descriptions, (c) dispatcher validation — all three from one computation → searches run narrow with auto-fallback.
**Invariant:** The prompt contract and the dispatcher must never disagree about which scopes exist in a run; offering `all` without ≥2 real scopes invites pointless fan-out; defaulting wide instead of narrow leaks cross-conversation docs into session answers.

**Probe:** `tests/unit/test_cuga_lite_knowledge_scopes.py::test_knowledge_scope_context_requires_thread_for_session_scope / test_e2b_serializes_knowledge_wrapper_scope_and_thread_context` — pins thread-gating and the E2B serialization of scope+thread context (26 slash-substitution tests pin the token layer separately).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "scope_context allowed scopes knowledge thread", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-computation mirror (prompt + dispatcher), synthetic-scope-only-with-fanout, narrowest-default-with-auto-fallback. Adapt scope names to your domains. Omit the synthetic scope if you have ≤1 store.
