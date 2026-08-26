<!-- capsule-v2 -->
# to_prompt_json — one serialization seam for every LLM prompt

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** when dozens of prompt templates interpolate structured context, where does JSON-serialization policy live so it can be changed once — and why does it default away from ASCII escaping?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/prompts/prompt_helpers.py:to_prompt_json` (:23–40) + constant `DO_NOT_ESCAPE_UNICODE` (:20); 41 call sites across `prompts/extract_nodes.py`, `extract_edges.py`, `extract_nodes_and_edges.py`, `dedupe_nodes.py`, `summarize_nodes.py`, `eval.py`, and `search/search_helpers.py`.
**Signature:** `to_prompt_json(data: Any, ensure_ascii: bool = False, indent: int | None = None) -> str` (defaults = minified, unicode-preserving).
**Data Shape:** takes any JSON-able context payload (entity dicts, edge lists, previous-episode lists); returns the exact string embedded into a prompt template slot like `{to_prompt_json(context['previous_episodes'])}`.

### Decisive source
```python
def to_prompt_json(data: Any, ensure_ascii: bool = False,
                   indent: int | None = None) -> str:
    """...By default (ensure_ascii=False), non-ASCII characters
    (e.g., Korean, Japanese, Chinese) are preserved in their original form in
    the prompt, making them readable in LLM logs and improving model understanding."""
    return json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
```

**Flow:** prompt modules build a plain-dict context → templates interpolate via `to_prompt_json` at 41 sites → the function is the single choke point for serialization policy (escaping, minification, future truncation/redaction).
**Invariant:** (1) `ensure_ascii=False` is deliberate — CJK text stays readable to the model AND in logs; flipping it to True silently degrades multilingual extraction quality; (2) minified by default (`indent=None`) because prompts are token budgets; (3) all structured context flows through this ONE helper — a porter who sprinkles raw `json.dumps` across templates forks the policy and loses the choke point.
**Probe:** no direct unit test for prompt_helpers.py (coverage caveat — verified by whole-file read + call-site census); behavior is indirectly pinned by prompt-snapshot evals under `tests/evals/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "to_prompt_json prompt_helpers ensure_ascii", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-helper serialization choke point with unicode-preserving defaults; adapt indent/truncation policy to your token budget; omit nothing — even if your host has one template today, route it through the helper.
