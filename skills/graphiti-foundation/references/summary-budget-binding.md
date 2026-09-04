<!-- capsule-v2 -->
# Summary budget constant binding — how does one character budget stay coherent across LLM prose AND code-side truncation?

**Source:** graphiti Apache-2.0 `main@993e081a`; Codebase Memory `graphiti`. **Question:** how do you stop prompt-text budgets and enforcement truncation from drifting apart as prompts evolve?

## MAX_SUMMARY_CHARS: one runtime constant, prompt fragments and two truncation styles
**Path/Symbol:** `graphiti_core/utils/text_utils.py:MAX_SUMMARY_CHARS` (:26); shared fragment `graphiti_core/prompts/snippets.py:summary_instructions` (:19-34); hard slice `graphiti_core/graphiti.py:545-546`; sentence-aware ladder `truncate_at_sentence` (text_utils.py:29) applied at `utils/maintenance/node_operations.py:1000` and `utils/maintenance/community_operations.py:155,:199`; pin `tests/test_text_utils.py:89-102`.
**Signature:** `MAX_SUMMARY_CHARS = 1000`; `def truncate_at_sentence(text: str, max_chars: int) -> str`.
**Data Shape:** the constant is interpolated into f-string PROMPT PROSE at import time and read by ENFORCEMENT code at run time — same module-level value, two consumption modes.

### Decisive source
```python
# text_utils.py :26 — single definition:
MAX_SUMMARY_CHARS = 1000

# snippets.py :17,:19,:22 — shared prompt fragment imports the CODE constant:
from graphiti_core.utils.text_utils import MAX_SUMMARY_CHARS
summary_instructions = f"""Guidelines:
        3. Keep the summary information-dense and entity-specific.
        STATE FACTS DIRECTLY IN UNDER {MAX_SUMMARY_CHARS} CHARACTERS."""

# graphiti.py :544-546 — orchestrator saga path enforces with a HARD slice:
summary = llm_response.get('summary', '')
if len(summary) > MAX_SUMMARY_CHARS:
    summary = summary[:MAX_SUMMARY_CHARS]
```

**Flow:** text_utils defines 1000 once → `prompts/snippets.py` builds a reusable guideline fragment interpolating it; `extract_nodes.py` embeds that fragment at TWO sites (:479, :521) and `summarize_nodes.py` at :96, while `summarize_sagas.py` interpolates it into a pydantic field DESCRIPTION (:29) and prompt line (:67) → after generation, enforcement applies per call-site style: the orchestrator saga summarizer HARD-slices to exactly N chars, background maintenance paths use sentence-boundary-aware `truncate_at_sentence`, and node summaries get the sentence-aware cut inside `node_operations` → `tests/test_text_utils.py:90` pins the value so silent retuning fails CI.
**Invariant:** the prompt promise ('UNDER {N} CHARACTERS') and post-hoc truncation reference the SAME runtime constant — retuning the budget is a one-line diff that cannot desynchronize instructions from enforcement. Enforcement STYLE is deliberately split: hot orchestrator path pays O(1) hard slice; background community/node maintenance pays the sentence-boundary scan for readability. Do not unify the styles blindly — they encode different latency/readability tradeoffs.
**Probe:** `.venv/bin/python -m pytest tests/test_text_utils.py -q` — RE-EXECUTED pass 11 (verification pass), 11 passed: pins the constant value (`== 1000`, :88-90) and sentence-boundary behavior incl. realistic-summary case. Fragment-consumer wiring verified by grep + source read: `summary_instructions` built in snippets.py (:17-22), interpolated by extract_nodes.py + summarize_nodes.py; hard slice graphiti.py:544-546 read directly; sentence-aware cuts confirmed at node_operations.py:1000 (coverage-flagged metadata_changed → range read from source) and community_operations.py:155,:199.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "MAX_SUMMARY_CHARS summary_instructions truncate_at_sentence", limit: 10 });
```

## Verdict
Adopt the bind-prompts-to-code-constants pattern for ANY numeric budget an LLM is instructed to respect. Adapt the fragment mechanism: a plain shared f-string suffices until you need versioned prompt modules (see `prompt-library`). Omit dual enforcement styles only when all your consumers share one latency class.
