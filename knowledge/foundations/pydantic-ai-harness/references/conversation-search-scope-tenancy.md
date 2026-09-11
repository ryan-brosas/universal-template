<!-- capsule-v2 -->
# Conversation-scoped search: fail-closed tenancy for shared history stores

## Source / Question
`pydantic_ai_harness/conversation_search/_toolset.py` + `_capability.py` — When one store holds MANY principals' conversation history, how do you scope a recall tool to the caller's conversation without turning it into a cross-tenant read primitive? Porters default to store-wide search and leak verbatim excerpts across conversations.

## Path / Symbol
`conversation_search/_toolset.py` — `SearchScope = Literal['all', 'conversation']` (:68–76), scope branch in `search_conversation_history` (:343–354), run filter in `_load_sections` (:403–408), same-answer rule (:357–360), scope note appended to tool description (:319–321, :63–66); `conversation_search/_capability.py` — `scope: SearchScope = 'all'` docstring (:63–72).

## Signature
```python
if self._scope == 'conversation':
    if ctx.conversation_id is None:
        return 'Conversation-scoped search needs a conversation id, ...'   # searches NOTHING
    conversation_id = ctx.conversation_id
...
runs = [run for run in runs if run.conversation_id == conversation_id]
```

## Data Shape
Scope is a capability-level config (`ConversationSearch.scope`, default `'all'`). Under `conversation`: corpus = runs whose `conversation_id` matches the calling run's; an unlabelled calling run gets a corrective text answer; a scoped `run_id` that exists but belongs to another conversation answers exactly like an unknown one.

### Decisive source
1. **Fail closed** (:345–348): "Filtering on `conversation_id is None` would match every unlabelled run in the store, which is the exposure the scope exists to prevent, so an unlabelled run searches nothing rather than everything."
2. **Same-answer rule** (:357–360): absent vs out-of-scope `run_id` return the SAME message — "a distinct message would tell the model which run ids exist in other conversations."
3. **Announced in the description** (:63–66): the tool description gains "This search covers only the current conversation…" so the model knows the boundary before calling.
4. **Default stays wide by design**: `all` is correct for single-principal stores (the shape pydantic-ai-harness#124 asks for); scoping is opt-in per deployment.

## Flow / Invariant
Resolve scope → missing conversation_id ⇒ immediate non-searching answer → filter `list_runs()` by conversation_id THEN by optional run_id → rank. Invariant: under `conversation`, no query can surface excerpts from another conversation — not even existence information about foreign run ids.

## Probe (direct test)
`tests/conversation_search/test_conversation_search.py::TestSearchScope`: `test_conversation_scope_hides_other_conversations` (:493), `test_conversation_scope_blocks_an_out_of_scope_run_id` (:500), `test_conversation_scope_without_a_conversation_id_searches_nothing` (:506), `test_conversation_scope_is_announced_in_the_tool_description` (:515), `test_default_scope_spans_every_conversation` (:487).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'SearchScope conversation_id fail closed scope'`

## Verdict
**Adopt** fail-closed scoping for ANY retrieval tool over multi-tenant history: unknown identity ⇒ empty result with guidance, never fallback-to-everything. **Adopt** the identical-error rule to avoid leaking corpus shape. **Adapt** the scope vocabulary to your tenancy model.
