<!-- capsule-v2 -->
# Code-action step spine — how does model text become executed code and then an observation?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** In `CodeAgent._step_stream`, what is the ordered pipeline from LLM response to sandbox execution, and which two stop-sequence/tag invariants prevent truncated or unterminated code actions?

## Parse → fix → execute → observe
**Path/Symbol:** `src/smolagents/agents.py:CodeAgent._step_stream` (:1638-1764); parsing helpers `parse_code_blobs`/`extract_code_from_text` (`utils.py:189-251`); `fix_final_answer_code` (`local_python_executor.py:332-357`).
**Signature:** `_step_stream(memory_step: ActionStep) -> Generator[ChatMessageStreamDelta | ToolCall | ToolOutput | ActionOutput]`; `parse_code_blobs(text, code_block_tags) -> str`; `fix_final_answer_code(code) -> str`.
**Data Shape:** `code_block_tags` defaults to `("<code>", "</code>")`, or `("```python", "```")` for `code_block_tags="markdown"`; every code action becomes exactly ONE synthetic `ToolCall(name="python_interpreter", arguments=code_action, id=f"call_{len(self.memory.steps)}")`.

### Decisive source
```python
# :1651-1654 — the closing-tag stop-sequence carve-out:
stop_sequences = ["Observation:", "Calling tools:"]
if self.code_block_tags[1] not in self.code_block_tags[0]:
    # If the closing tag is contained in the opening tag, adding it as a stop sequence would cut short any code generation
    stop_sequences.append(self.code_block_tags[1])
# :1693-1695 — auto-append keeps history well-formed even when the model forgets to close:
if output_text and not output_text.strip().endswith(self.code_block_tags[1]):
    output_text += self.code_block_tags[1]
    memory_step.model_output_message.content = output_text   # history sees the FIXED text
```

**Flow:** (1) generate with stop_sequences (closing tag suppressed when contained in the opener — markdown case — else generation dies at the fence it hasn't written yet); (2) if not structured-output mode, append the missing closer AND rewrite `model_output_message.content` so subsequent prompts teach the model the ending convention (test-pinned `test_end_code_appending`); (3) parse via custom tags → markdown fallback → raw-AST passthrough, with a dedicated "final_answer(...)" hint error when the text mentions final+answer; (4) `fix_final_answer_code` renames assignments to `final_answer` into `final_answer_variable` ONLY when a call also exists (guard :341-344 — without a call the rewrite would corrupt the model's memory of its own variables), preserving calls; (5) execute through `self.python_executor`, unauthorized-import failures add user-facing advice naming `additional_authorized_imports`; on ANY execution error the already-captured print outputs are salvaged into the observation before raising AgentExecutionError (:1735-1743); (6) success path builds `"Execution logs:\n...\nLast output from code snippet:\n<value>"` as the observation.
**Invariant:** History is always rewritten to the *fixed* form (closer appended) but never to a fabricated result — observations carry real logs plus the truncated last value. The parse ladder must try custom tags BEFORE markdown, else ```` ```python ```` inside `<code>` blocks double-strips.
**Probe:** `tests/test_agents.py::test_end_code_appending` (:2184-2209, asserts every ActionStep output ends with the closer), `tests/test_local_python_executor.py::test_fix_final_answer_code` (:2139-2177 parametrized). Live: agent whose fake model omits `</code>` → memory outputs all end with the closer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "CodeAgent _step_stream parse_code_blobs code_block_tags stop_sequences", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the pipeline order and both tag invariants. Adapt tags/structured-output branch per host model. Omit `fix_final_answer_code`'s guard and you corrupt multi-step variable state; omit the closer-append and weak models never learn to terminate.
