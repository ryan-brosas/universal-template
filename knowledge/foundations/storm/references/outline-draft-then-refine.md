<!-- capsule-v2 -->
# Outline draft-then-refine — how does a noisy research conversation become a second, better outline without regressing to the topic-only draft?

**Source:** storm MIT `main@fb951af7744dab086e34962e9bc6fe878e145f83`; Codebase Memory `storm`. **Question:** What is the exact choreography between the topic-only outline draft and the conversation-guided refinement — and what must be cleaned from the conversation before the LM ever sees it?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/storm_wiki/modules/outline_generation.py:WriteOutline.__init__` (:78–82) + `WriteOutline.forward` (:84–125) + `WritePageOutline` (:128–137) + `WritePageOutlineFromConv` (:153–167).
**Signature:** `forward(topic, dlg_history, old_outline=None, callback_handler=None) -> dspy.Prediction(outline, old_outline)`.
**Data Shape:** `dlg_history`: List[DialogueTurn] (agent_utterance/user_utterance strings). `old_outline`: caller-injectable pre-cleaned draft; internally produced by `draft_page_outline(topic)` then passed through `clean_up_outline`. Conversation flattened as `"Wikipedia Writer: {q}\nExpert: {a}"` lines.

### Decisive source
```python
# dialogue denoising BEFORE the LLM sees it:
if ("topic you" in turn.agent_utterance.lower()
        or "topic you" in turn.user_utterance.lower()):
    continue                       # drop prompt-echo noise turns entirely
conv = ArticleTextProcessing.remove_citations(conv)               # [n] scrub
conv = ArticleTextProcessing.limit_word_count_preserve_newline(conv, 5000)
# two-stage generation: topic-only DRAFT, then conv-guided REFINE:
if old_outline is None:
    old_outline = ArticleTextProcessing.clean_up_outline(
        self.draft_page_outline(topic=topic).outline)
    callback_handler.on_direct_outline_generation_end(outline=old_outline)
outline = ArticleTextProcessing.clean_up_outline(
    self.write_page_outline(topic=topic, old_outline=old_outline, conv=conv).outline)
callback_handler.on_outline_refinement_end(outline=outline)
```
The refine signature feeds the draft through an **OutputField**, not an InputField:
```python
class WritePageOutlineFromConv(dspy.Signature):
    old_outline = dspy.OutputField(prefix="Current outline:\n", format=str)
```

**Flow:** Turns mentioning "topic you" are dropped → surviving dialogue citation-stripped and word-capped at 5000 → if no caller-supplied draft, a topic-only `WritePageOutline` call produces one (cleaned, announced via callback) → a second `WritePageOutlineFromConv` call improves that draft against the conversation → BOTH outlines pass `clean_up_outline`; the tuple `(refined, draft)` is returned so callers can compare or fall back.
**Invariant:** (1) The refine call ALWAYS runs; only the draft is conditional on `old_outline is None` — a caller can inject a human/hand-made outline and skip stage one. (2) The draft is never mutated in place; the refined output is separately cleaned, so a degenerate refine still leaves the draft intact for comparison. (3) `clean_up_outline` runs on BOTH stages — raw LM headings must never reach the tree parser. (4) The old-outline-as-OutputField trick means the draft enters the prompt via the literal `"Current outline:\n"` prefix; re-declaring it as an InputField changes prompt layout and degrades adherence.
**Probe:** deterministic pins GREEN this pass — direct byte-reads of outline_generation.py:91–106 (trim filter + remove_citations + 5000 cap), :108–123 (conditional draft / unconditional refine / callback points), :163 (`old_outline` OutputField declaration), :78–82 (Predict wiring); knowledge_curation.py `_get_considered_personas` :281–284 confirms personas feed the conversation upstream. Live retrieve executed this pass: `search_graph(project="storm", query="WriteOutline draft refine old outline conversation")` ranked `WriteOutline.__init__ :78-82` #2 and `WriteOutline.forward :84-125` #3 (rank 1 was the Co-STORM warm-start twin — expected vocabulary overlap).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "WriteOutline draft refine old outline conversation", limit: 10 });
```

## Verdict
Adopt the two-stage draft→refine split with an injectable draft slot for any outline/plan pipeline fed by noisy agent transcripts; adapt the noise-filter phrase list and word caps; omit the dspy OutputField mechanism itself if your framework has first-class multi-input prompts (but keep the "current draft labeled in-prompt" idea). Caveat: no upstream tests exist at pin; source-pinned deterministic evidence.
