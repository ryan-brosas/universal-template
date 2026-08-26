<!-- capsule-v2 -->
# Run-loop exit machine — when does the agent loop stop, and what happens at max steps?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What are the exact loop-exit conditions of `_run_stream`, how does a step's final answer terminate the run, and what does the caller receive when the step budget is exhausted?

## Generator-driven ReAct loop
**Path/Symbol:** `src/smolagents/agents.py:MultiStepAgent._run_stream` (:540-611), `run` (:436-538), `_handle_max_steps_reached` (:625-637), `interrupt`/`interrupt_switch` (:470, :754-756).
**Signature:** `run(task, stream=False, reset=True, images=None, additional_args=None, max_steps=None, return_full_result=None) -> Any | RunResult`; `_run_stream(...) -> Generator[ActionStep | PlanningStep | FinalAnswerStep | ChatMessageStreamDelta]`.
**Data Shape:** Non-stream mode materializes `list(self._run_stream(...))` and asserts the LAST element is a `FinalAnswerStep`; stream mode yields the same event sequence live (ToolCall → ActionOutput → ActionStep per iteration).

### Decisive source
```python
# :543-604 — the whole exit machine in one while:
while not returned_final_answer and self.step_number <= max_steps:
    if self.interrupt_switch: raise AgentError("Agent interrupted.", self.logger)
    ... planning cadence gate ...
    try:
        for output in self._step_stream(action_step):
            yield output
            if isinstance(output, ActionOutput) and output.is_final_answer:
                if self.final_answer_checks: self._validate_final_answer(final_answer)
                returned_final_answer = True
                action_step.is_final_answer = True
    except AgentGenerationError as e: raise e          # implementation bug → abort everything
    except AgentError as e: action_step.error = e      # model-caused → feed back as observation
    finally:
        self._finalize_step(action_step); self.memory.steps.append(action_step)
        yield action_step; self.step_number += 1
if not returned_final_answer and self.step_number == max_steps + 1:
    final_answer = self._handle_max_steps_reached(task)
```

**Flow:** Four exits exist: (1) final answer observed on an ActionOutput (after optional `final_answer_checks`, whose failure raises and is recorded as the step error — the check failing does NOT abort, it becomes the step's error and the loop continues); (2) step budget exhausted → forced `provide_final_answer` call wrapped in an extra ActionStep carrying `AgentMaxStepsError` (`state="max_steps_error"` under `return_full_result=True`; test pins memory length task+max+1); (3) interrupt switch checked between steps only (cooperative, callback-driven); (4) AgentGenerationError propagates immediately because it means OUR plumbing is broken, not model flakiness. The final answer value passes through `handle_agent_output_types` before yielding FinalAnswerStep.
**Invariant:** Error asymmetry is load-bearing: AgentError subclasses = model's fault → logged into `action_step.error` and rendered back to the LLM with retry coaching ("Now let's retry: take care not to repeat previous errors!"); AgentGenerationError = harness fault → crash. Collapsing the two turns every transient provider hiccup into a dead run.
**Probe:** `tests/test_agents.py::test_fails_max_steps` (:501-521, asserts steps count 7 and `AgentMaxStepsError` type), `test_interrupt` (:1429-1448), `test_final_answer_checks` (:664). Live: fake-model CodeAgent with `executor` returning `is_final_answer=False` and `max_steps=2` → last memory step `.error` is AgentMaxStepsError and run returns.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "_run_stream returned_final_answer max_steps interrupt_switch", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the four-exit machine verbatim including generator semantics (streaming consumers rely on ActionStep being yielded AFTER its outputs). Adapt max-step recovery (smolagents spends one more LLM call to summarize; cheaper hosts can return a sentinel). Omit nothing from the finally block: finalize→append→yield→increment ordering is what keeps memory consistent even when the step raised.
