<!-- capsule-v2 -->
# Regenerate always forks — What exactly does regenerate drop, and why must it mint a new run_id?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** Which messages does a regenerate boundary remove, and how do the sugar params resolve?

## Drop only trailing no-tool-call assistant turns; fork is derived, never passed
**Path/Symbol:** `libs/agno/agno/agent/_run.py:_find_regenerate_checkpoint` (:3093-3115) + `_normalize_regenerate_params` (:3164-3217) + `_resolve_continue_from` (:3129-3161).
**Signature:** `_find_regenerate_checkpoint(run_response: RunOutput) -> int`; `_normalize_regenerate_params(run_response, *, regenerate, replace_original, additional_instructions, fork, continue_index, input) -> tuple[bool, Optional[int], Optional[str]]`.
**Data Shape:** checkpoint = count of messages to KEEP; conflicts raise ValueError.

### Decisive source
```python
def _find_regenerate_checkpoint(run_response) -> int:
    """Regenerate semantics: drop ONLY the trailing
    assistant messages that have no tool_calls — i.e. the final response
    turn. Intermediate assistant messages with tool_calls and the tool
    results they produced are preserved, so the model regenerates a fresh
    summary of the same tool outputs without re-invoking the tools."""
    messages = run_response.messages or []
    i = len(messages)
    while i > 0 and messages[i - 1].role == "assistant" and not messages[i - 1].tool_calls:
        i -= 1
    if i == 0:
        raise ValueError("Cannot regenerate: run has no non-assistant messages to regenerate from.")
    return i

# ``regenerate`` ALWAYS forks. The 1-run-1-loop invariant demands a new
# run_id whenever the source run's loop has already completed —
# ``replace_original`` controls a separate concern (whether the source
# is marked REGENERATED and hidden from history), not whether to fork.
return (True, _find_regenerate_checkpoint(run_response), resolved_input)
```

**Flow:** regenerate=True → reject explicit fork (ValueError) → compute checkpoint by backward walk → resolve to `(fork=True, index, input=additional_instructions)` → continue dispatch truncates via the pair-safe path. `_resolve_continue_from` keeps `"last_user"` DISTINCT from regenerate: last_user drops trailing assistant AND intermediate tool exchanges; regenerate keeps them.
**Invariant:** Regenerate re-summarizes existing tool outputs without re-invoking tools — cutting into tool_call batches would either orphan calls or force re-execution. Forking is mandatory because a completed run's loop is closed; mutating its tail in place would break the one-run-one-loop ledger. `replace_original` only toggles history visibility of the source.
**Probe:** `grep -c '(True, _find_regenerate_checkpoint(run_response), resolved_input)' libs/agno/agno/agent/_run.py` → **1**; direct behavior tests `libs/agno/tests/unit/agent/test_unified_continue.py::TestTruncateHelper` (:678, incl. `test_truncate_drops_tools_for_removed_messages`, `test_truncate_filters_requirements`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_find_regenerate_checkpoint _normalize_regenerate_params", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the backward-walk checkpoint rule and the regenerate⇒fork derivation with its conflict errors; adapt status-marking of hidden sources to your session schema; omit additional_instructions aliasing if you expose input directly.
