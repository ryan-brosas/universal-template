<!-- capsule-v2 -->
# Evidence context build contract — what is the structured contract between the summary LLM's output and the Context object?

**Source:** paper-qa Apache-2.0 `main@57e89f72`; Codebase Memory `paper-qa`. **Question:** How does one text chunk (with optional media) become a scored, citation-safe Context, and which JSON keys are load-bearing?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/core.py:_map_fxn_summary` (:178-380). Error/retry shell is owned separately by `evidence-context-retry-taxonomy`; score-extraction regex internals by `citation-strip-score-ladder`.
**Signature:** `async def _map_fxn_summary(text: Text, question: str, summary_llm_model: LLMModel | None, prompt_templates: tuple[str, str] | None, extra_prompt_data=None, parser=None, callbacks=None, skip_citation_strip=False, evidence_text_only_fallback=False, _prior_attempt=None) -> tuple[Context, list[LLMResult]]`.
**Data Shape:** Input `Text` carries `.text`, `.name`, `.doc` (formatted_citation), `.media`. Parser must return a dict with at least `summary`; recognized keys are `summary` (context body), `relevance_score` (int), `question` (popped — mis-parse guard); every OTHER key becomes an extras field merged onto the Context.

### Decisive source
```python
unique_media = list(dict.fromkeys(text.media))            # order-preserving dedup
table_texts = [m.text for m in unique_media if m.info.get("type") == "table" and m.text]
"text": text_with_tables_prompt_template.format(...) if table_texts else cleaned_text
...
message = create_multimodal_message(text=message_prompt,
           image_urls=[i.to_image_url() for i in unique_media]) if unique_media else Message.create_message(...)
...
context = result_data.pop("summary")
score = result_data.pop("relevance_score") if "relevance_score" in result_data else extract_score(context)
result_data.pop("question", None)      # stripped because it can be mis-parsed from outputs
extras = result_data                   # leftover keys ride onto the Context
...
return Context(context=context, question=question,
    text=Text(doc=text.doc.model_dump(exclude={"embedding"}),
              **text.model_dump(exclude={"embedding", "doc"})),
    score=score, **extras)
```

**Flow:** clean chunk text (`strip("\n")`, `"(no text)"` fallback) → splice table-type media into the prompt body while images attach as a multimodal message → single evidence call tagged `name="evidence:" + text.name` → parse JSON (or raw prose) → key algebra (summary / relevance_score-or-extract_score / question-pop / extras-passthrough) → strip colliding citations unless `skip_evidence_citation_strip` → rebuild the Text WITHOUT embeddings.
**Invariant:** The embedding drop is deliberate and documented in-source: "Once we already have Contexts, we filter them by score (and not the underlying Text's embeddings), so embeddings can be safely dropped from the deepcopy." With no model/prompts configured, the context IS the raw chunk and score defaults to 5 ("we filter out 0s in another place") — so downstream score filters must treat 0 as irrelevant and never rely on embeddings past this point. A text-only media fallback records `extras["used_images"] = False`.
**Probe:** `tests/test_paperqa.py::test_json_evidence` (:875-922) pins that extras like `author_name` land on Context objects while sentinel values from broken JSON do not survive; `::test_evidence` (:814-836) pins scoreless-context replacement via retry. Deterministic source/test-range probe (no runner provisioned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "_map_fxn_summary parser relevance_score extras multimodal", limit: 10 });
```

## Verdict
Adopt the key algebra (required summary, preferred explicit score over heuristic extraction, question-key stripping, extras passthrough), table-splicing into the summary prompt, and the embedding-dropping Context rebuild; adapt the multimodal message construction to your provider SDK; omit litellm BadRequest/Timeout wrapping (retry-taxonomy capsule owns it). Coverage: core.py no_recorded_issue + metadata_match @ gen 2026-08-25T19:57:59Z.
