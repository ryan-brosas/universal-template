<!-- capsule-v2 -->
# GradioUI streaming surface — how does the chat UI consume the run generator, and which output shapes need cleanup?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** How does `gradio_ui.py` turn the `_run_stream` event sequence into incremental chat messages, and what trailing-tag artifacts does it scrub from model output?

## Generator-to-chat-message pump
**Path/Symbol:** `src/smolagents/gradio_ui.py` — `_clean_model_output` (:44-59), `get_step_footnote_content` (:30-40), stream_puller over agent.run(stream=True) (module body, pulls ChatMessageStreamDelta/ActionStep/PlanningStep/FinalAnswerStep), imports :17-26.
**Signature:** `_clean_model_output(model_output: str) -> str`; footnote builder renders token counts + rounded duration into an HTML span.
**Data Shape:** UI message accumulation keyed by step; code blocks re-rendered from ActionStep.code_action; FinalAnswerStep terminates the pull loop.

### Decisive source
```python
# :52-56 — three artifact spellings of "</code>-before-fence", all normalized:
model_output = re.sub(r"```\s*<end_code>", "```", model_output)   # handles ```<end_code>
model_output = re.sub(r"<end_code>\s*```", "```", model_output)   # handles <end_code>```
model_output = re.sub(r"```\s*\n\s*<end_code>", "```", model_output)  # ```\n<end_code>
return model_output.strip()
```

**Flow:** The UI iterates the same generator a headless consumer would: stream deltas append to the live bubble (agglomerated for markdown rendering), ToolCall events announce intent, ActionStep completion swaps in observations/logs with a duration+token footnote span, PlanningStep renders its plan block, and FinalAnswerStep both finalizes the assistant message and breaks. Model outputs that end mid-fence (because the agent appended the closer into history but the raw content still carries `<end_code>` variants) are normalized before display so users never see protocol tags.
**Invariant:** The pump must tolerate ANY interleaving of the StreamEvent union because the generator yields provider deltas and step objects concurrently — buffering per step-number rather than assuming order is what keeps partial streams renderable. Tag cleanup covers three spellings because different stop-sequence configs leave different residue.
**Probe:** `tests/test_gradio_ui.py` (stream-puller cases incl. image/audio steps). Live: feed `_clean_model_output("x\n```\n<end_code>")` → `"x\n```"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "_clean_model_output get_step_footnote_content gradio stream", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt event-typed pumping over the shared generator rather than a bespoke loop. Adapt footnote HTML to your UI kit. Omit tag scrubbing only if your UI never displays raw model_output.
