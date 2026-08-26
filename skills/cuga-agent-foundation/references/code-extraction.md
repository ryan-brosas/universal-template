<!-- capsule-v2 -->
# Fenced-code extraction — the print()-gate unification decision and probing-tool isolation

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A code-executing agent must turn a model response (fenced blocks, raw text, or reasoning) into runnable Python, and must ensure a "probe" tool that has no declared output schema runs ALONE in its own turn before dependent code. What extraction rules and truncation invariants make that safe?

## The extractor
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/execution/code_extraction.py` (`extract_and_combine_codeblocks` :23-56, `extract_code_from_model_response` :103-117, `make_tool_awaitable` :120-148, `_recover_non_closing_python_fence` :151-173).
**Signature:** `extract_and_combine_codeblocks(text, tools_needing_probing=frozenset()) -> str`; `extract_code_from_model_response(content, reasoning_content, tools_needing_probing=frozenset()) -> str`.
**Data Shape:** `BACKTICK_PATTERN = r"```python(.*?)```"` (DOTALL). Returns joined fenced blocks; falls back to an unclosed-fence recovery, then to raw text only if it contains `print(` and compiles.

### Decisive source
```python
# code_extraction.py:47-56 — the print() gate applies ONLY to the no-fence raw-text fallback.
# Fenced ```python blocks are returned even with no print() call (canonical Lite behaviour —
# the user explicitly chose this over Supervisor/code_act's print() gate).
stripped_text = text.strip()
if "print(" not in stripped_text:
    return ""
try:
    compile(stripped_text.replace("await ", ""), "<string>", "exec")
    return _truncate_after_first_probing_line(stripped_text, tools_needing_probing)
except SyntaxError:
    return ""

# code_extraction.py:151-173 — unclosed ```python fence recovery, compile-guarded, walks back line-by-line
# so trailing prose after otherwise-valid code is salvageable: `print("x")\nhope this helps` → `print("x")`
```

**Flow:** fenced blocks found → strip each, truncate after the first probing block, join with `\n\n`. No fences → recover unclosed fence (compile-guarded, walk back to a compiling prefix). Still nothing → raw-text path gated on `print(` + compile. `extract_code_from_model_response` tries `content` first, falls back to `reasoning_content`. Probing truncation: block-level for fenced, statement-level for recovered/raw (grow the cut until everything up to `end` compiles, so a multiline probing call like `res = await file_readfile(\n "x"\n)` is kept whole — truncating at the first line alone yields an unclosed paren and the probe never runs). `make_tool_awaitable` always returns a coroutine; sync funcs run in the default executor; Pydantic results are `.model_dump()`-ed.
**Invariant:** A probing tool (no declared output schema, not yet observed this session) must never run in the same turn as later dependent code — a fresh model turn with the real tool result visible runs before anything that depends on the probe. `await ` is stripped before `compile` so async tool calls parse as valid Python.
**Probe:** `tests/execution/test_code_extraction.py` pins the content-over-reasoning preference, the reasoning fallback, and the always-a-coroutine + Pydantic-dump contract of `make_tool_awaitable`; comprehensive cases live in `cuga_lite/executors/tests/test_extract_codeblocks.py` and `test_sync_async_tools.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "extract_and_combine_codeblocks tools_needing_probing make_tool_awaitable print gate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fenced-block-without-print() decision, the compile-guarded unclosed-fence recovery, the probing-tool truncation (block-level then statement-level with compile-grown cuts), and the always-awaitable + Pydantic-dump tool wrapper. Adapt the probing-tool set to your tools. Omit the `await `-stripping if your executor doesn't need it.
