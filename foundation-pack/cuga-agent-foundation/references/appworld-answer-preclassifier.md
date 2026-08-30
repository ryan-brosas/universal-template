<!-- capsule-v2 -->
# AppWorld answer pre-classifier — why does an ACTION task answer "N/A" before extraction ever runs?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does the plain-mode final-answer agent avoid failing benchmark scoring on update tasks, and what is the classifier's failure default?

## Classify-then-skip with QUERY-on-failure default
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/answer/final_answer_agent/final_answer_agent.py:_is_action_task` (:115-129), `_na_final_answer` (:131-138), classifier chain wiring (:59-65), `run` (:83-96); label parser `prompts/load_prompt.py:is_appworld_action_label`.
**Signature:** `run(input_variables: AgentState) -> AIMessage`; `ainvoke_with_retry_on_retry_on_tool_choice_none` wraps the extraction chain (`llm/errors.py`).
**Data Shape:** classifier = free-text chain (no structured output) → `is_appworld_action_label(raw)` parses; N/A payload `FinalAnswerAppworldOutput(thoughts=[...], final_answer="N/A", final_answer_type="str")`.

### Decisive source
```python
            # Classify the task first: AppWorld grades an answer for EVERY task, and for
            # action/update tasks the ground-truth answer is null — so returning any value
            # fails the "answers match" check. A dedicated ACTION-vs-QUERY call is more
            # reliable than relying on the extraction prompt to also self-classify.
            self.classifier_chain = BaseAgent.get_chain(
                load_appworld_task_classifier_prompt(), llm, wx_json_mode="no_format"
            )
```
```python
        except Exception as e:
            logger.warning(f"FinalAnswer action/query classifier failed, defaulting to QUERY: {e}")
            return False
```

**Flow:** appworld_plain mode only — before extraction, a dedicated classifier call decides ACTION vs QUERY; ACTION ⇒ return "N/A" immediately (eval maps it to null ground truth), skipping extraction entirely (flag-gated by `appworld_classify_action_tasks`, default True). QUERY ⇒ extraction via `ainvoke_with_retry_on_tool_choice_none` + post-LLM runnable. Any classifier error ⇒ False (QUERY) so an answer is still produced — never null-out a task that needed one.
**Invariant:** The dedicated-classifier-over-self-classification decision is deliberate (comment pins it): one small prompt beats asking the extractor to also classify. Fail-open to QUERY preserves recall of real answers at the cost of occasional wrong non-null answers on misclassified ACTION tasks.
**Probe:** Direct test `tests/unit/test_appworld_action_classifier_label.py` pins label parsing. Deterministic: `grep -n "defaulting to QUERY" src/cuga/backend/cuga_graph/nodes/answer/final_answer_agent/final_answer_agent.py` hits :128.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_is_action_task FinalAnswerAppworldOutput is_appworld_action_label classifier_chain", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the separate cheap classifier ahead of expensive generation when downstream grading punishes a class of outputs, and the fail-open-to-more-informative default. Adapt labels/answer sentinels to your eval harness. Omit entirely outside AppWorld-style benchmarks.
