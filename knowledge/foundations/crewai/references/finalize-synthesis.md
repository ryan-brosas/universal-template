<!-- capsule-v2 -->
# Finalize synthesis — how does the run end with a guaranteed AgentFinish even when no LLM ever produced one?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How does finalize dedupe concurrent triggers, synthesize from todo results, and decide when the last todo result IS the answer?

## AgentExecutor.finalize
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:2331-2411` (`finalize`), `:2413-2442` (`_can_use_last_todo_result_as_final_answer`), `:2444+` (`_synthesize_final_answer_from_todos`).
**Signature:** `def finalize(self) -> Literal["completed", "skipped"]`, listening on `or_("all_todos_complete", "agent_finished", "tool_result_is_final", "native_finished")`.
**Data Shape:** Sets `state.current_answer = AgentFinish(thought, output, text)`, `state.is_finished = True`. Returns `"skipped"` when current_answer is a non-finish type at entry.

### Decisive source
```python
# Guard against duplicate finalization — the flow may trigger finalize
# more than once when concurrent branches both reach a terminal state.
with self._finalize_lock:
    if self._finalize_called:
        return "completed"
    self._finalize_called = True
# ... (separate flag from is_finished "because is_finished should only be
#  set when finalization succeeds")

if self.state.current_answer is None:            # Plan-and-Execute path
    todos_with_results = [t for t in self.state.todos.items if t.result]
    if todos_with_results:
        if self._can_use_last_todo_result_as_final_answer(todos_with_results):
            last_todo = max(todos_with_results, key=lambda t: t.step_number)
            final_text = str(last_todo.result or "")
            self.state.current_answer = AgentFinish(
                thought="Final answer returned directly from last completed todo",
                output=final_text, text=final_text)
        else:
            self._synthesize_final_answer_from_todos()   # one LLM call

if self.state.current_answer is None:            # last resort — never None
    fallback_text = "Agent completed execution but produced no final output."
    ...partial step results joined if any...
```

**Flow:** Any of four terminal labels → atomic check-and-set → if no explicit answer: try direct reuse of the strongest todo result, else one synthesis LLM call over `Step N (description): result` blocks (the ONLY place `response_model` applies on this path; concatenation fallback on synthesis failure), else deterministic fallback text → require AgentFinish → set finished → `_show_logs`.
**Invariant:** The skip-synthesis gate is deliberately strict — ALL must hold: no `response_model` requested, last-by-step-number todo has NO `tool_to_use`, non-empty result not starting `"error:"` and not containing `"tool execution error"`, AND (`len ≥ 200` chars or `≥30` words) with sentence punctuation. Anything weaker would ship truncated tool dumps as final answers. `_finalize_called` must be reset by invoke before each run (`test_finalize_called_reset_in_invoke*`) and set by `_complete_feedback` after human-feedback reruns so late triggers don't clobber the reviewed answer.
**Probe:** `tests/agents/test_agent_executor.py::TestFinalize.test_finalize_success / test_finalize_skips_synthesis_for_strong_last_todo_result / test_finalize_keeps_synthesis_when_response_model_is_set` + `TestExecutorStateReset` pair.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "AgentExecutor finalize replan todos", limit: 8, detail: "ids" });
// → AgentExecutor.finalize Method …/experimental/agent_executor.py 2339-2411
```

## Verdict
Adopt lock-guarded single-finalization plus the three-tier answer ladder (explicit → strong-last-todo → synthesized → fallback); adapt the quality heuristic to your output language; omit the LLM synthesis call if your host prefers raw concatenation (losing coherent structured output).
