<!-- capsule-v2 -->
# Expert action grammar — how does an LLM speaker decide between asking and answering without free-form drift?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How do you force a conversational agent to commit to one of a few contribution types, and route each type to the right generation path, when the planner's output is untrusted text?

## Four-action grammar + bracketed parse ladder
**Path/Symbol:** `knowledge_storm/collaborative_storm/modules/costorm_expert_utterance_generator.py:CoStormExpertUtteranceGenerationModule` — `GenExpertActionPlanning` (:17-39), `parse_action` (:59-71), `forward` (:103-160), `polish_utterance` (:73-101).
**Signature:** `parse_action(action: str) -> Tuple[str, str]`; `forward(topic: str, current_expert: str, conversation_summary: str, last_conv_turn: ConversationTurn)`.
**Data Shape:** Action types are exactly `["Original Question", "Further Details", "Information Request", "Potential Answer"]`; output is `(type, content)` or `("Undefined", "")`.

### Decisive source
```python
for action_type in action_types:
    if f"{action_type}:" in action:
        return action_type, trim_output_after_hint(action, f"{action_type}:")
    elif f"[{action_type}]:" in action:
        return action_type, trim_output_after_hint(action, f"[{action_type}]:")
return "Undefined", ""
...
if action_type == "Undefined":
    raise Exception(f"unexpected output: {action}")
```

**Flow:** If the previous turn was itself a question/request (`Original Question`/`Information Request`), planning is SKIPPED and the action is hard-set to `Potential Answer` with the last utterance as content. Otherwise the planner LM emits a one-sentence "note" starting with an action label; the parse ladder tries plain `Type:` then bracketed `[Type]:`, per type in list order. Answer-shaped actions (`Further Details`, `Potential Answer`) route through `AnswerQuestionModule(mode="brief", style="conversational and concise")` and copy its queries/cited_info into the turn; question/request actions pass the planned sentence through raw as the utterance. A separate polish stage rewrites the turn through `ConvertUtteranceStyle` with the previous expert utterance reduced by `extract_and_remove_citations` + `keep_first_and_last_paragraph`.
**Invariant:** (1) The OutputField is named `resposne` (typo) at :36 and is read verbatim as `.resposne` at :126 — renaming either side breaks the pipeline silently at attribute access; keep the pair byte-exact when porting. (2) `"Undefined"` must fail LOUD (raise), never fall back to a default action, or hallucinated labels poison dialogue history typing that downstream code keys on (`utterance_type` drives turn-policy counting and moderator windows). (3) The skip-planning shortcut means answer turns cost ONE LM call less only when the previous utterance_type is question-shaped — misclassifying types double-charges or starves grounding.
**Probe:** byte-pins executed this pass — :36 `resposne = dspy.OutputField(`, :126 `.resposne`, :59-71 dual-form ladder order, :139 Undefined raise, :87-88 question/request actions bypass grounded answering (`action_string = f"{action_type}"`). All line-exact against the checkout.
**Coverage caveat:** file checked `no_recorded_issue` @ gen 2026-08-25T20:09:07Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "CoStormExpertUtteranceGenerationModule parse_action GenExpertActionPlanning resposne", limit: 10 });
```

## Verdict
Adopt the constrained-label + fail-loud-parse pattern for any structured agent contribution (it is cheaper and sturdier than function-calling for plain-completion backends); adapt the label set to your domain; omit the typo by pairing BOTH occurrences if you rename, and keep the bracketed fallback only if your prompts show it.
