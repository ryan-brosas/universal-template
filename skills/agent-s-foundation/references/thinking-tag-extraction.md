<!-- capsule-v2 -->
# thinking-tag-extraction — How are reasoning and answer separated, and what happens when tags are missing?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** What is the exact split contract for `<thoughts>/<answer>` and its failure mode?

## Tag extraction seam
**Path/Symbol:** `gui_agents/s3/utils/common_utils.py:split_thinking_response` (:130-140); producer at `gui_agents/s3/core/engine.py:LMMEngineAnthropic.generate_with_thinking` (:128-152); consumers: code_agent.py :162, worker reflection :170, comparative_judge.py :138.
**Signature:** `split_thinking_response(full_response) -> Tuple[str, str]` returning `(answer, thoughts)` — NOTE the order.
**Data Shape:** Canonical form `<thoughts>\n...\n</thoughts>\n\n<answer>\n...\n</answer>`. Anthropic thinking mode synthesizes this envelope from the API's content blocks (thoughts = content[0].thinking, answer = content[1].text).

### Decisive source
```python
try:
    thoughts = full_response.split("<thoughts>")[-1].split("</thoughts>")[0].strip()
    answer   = full_response.split("<answer>")[-1].split("</answer>")[0].strip()
    return answer, thoughts
except Exception as e:
    return full_response, ""     # whole text becomes the "answer"
```

**Flow:** response → take text AFTER the LAST `<thoughts>` up to the FIRST following `</thoughts>`; same for `<answer>` → return (answer, thoughts). Any structure error ⇒ (full_response, "").
**Invariant:** (1) Because `str.split(x)[-1]` never raises, the except arm is nearly unreachable — a response with NO tags silently returns the ENTIRE text as answer with empty thoughts, it does NOT fail. Callers relying on thoughts emptiness as a validity signal (THOUGHTS_ANSWER_TAG_FORMATTER checks `[1] != ""`) get their gate for free. (2) Order of return is (answer, thoughts) while the parse order is thoughts-first — swap-prone. (3) The narrator prompt explicitly warns that missing tags invalidate the whole response (procedural_memory.py :315), i.e. enforcement lives in the format-checker layer, not here. (4) Anthropic non-thinking generate returns content[0].text only; thinking content is dropped unless use_thinking routes to generate_with_thinking.
**Probe:** `grep -n 'return full_response, ""' gui_agents/s3/utils/common_utils.py` → :140.
**Probe:** `grep -c 'split_thinking_response' gui_agents/s3/agents/code_agent.py` → 2 (import :5 + call site :162); `gui_agents/s3/bbon/comparative_judge.py` → 2 (import + call site :138).
**Probe:** `grep -n 'f"<thoughts>' gui_agents/s3/core/engine.py` → :150 (envelope construction line; note the literal `\n` escapes in the f-string make a `\\n`-containing probe pattern self-defeating — anchor on the opening tag).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "split_thinking_response thoughts answer", limit: 5 });
```

## Verdict
Adopt lenient tag-splitting with a strict tag-presence formatter upstream — leniency at parse, strictness at validation; adapt tag names; omit the Anthropic-specific envelope synthesis if your stack exposes reasoning natively. Beware the (answer, thoughts) return order.
