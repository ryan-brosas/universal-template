<!-- capsule-v2 -->
|# Multipart image return + conditional fallback stash — how do image blocks from a tool reach multimodal models without leaking memory on transports that can't carry them?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** A search tool extracts base64 images into results — when does it return multipart Parts vs stash a re-injection fallback, and who decides "multimodal"?

## Flag-gated Parts return; stash ONLY for non-native transports
**Path/Symbol:** `backend/python/app/agents/actions/retrieval/retrieval.py` :509–514 (authoritative flag), :666–675 (ImageBudget + collected_images through build_message_content_array), :703–728 (return branch).
**Signature:** return type `str | list[Part]`; gate = `if collected_images and is_multimodal_llm:` then `if not self.state.get("supports_multipart_tool_result", True): self.state.setdefault("pending_tool_images", []).extend(collected_images)`.
**Data Shape:** `is_multimodal_llm: bool` seeded onto tool_state from LLM config `isMultimodal`; `image_budget: ImageBudget` shared per-conversation on state; collected images are dicts convertible via `image_dict_to_part`.

### Decisive source
```python
# `is_multimodal_llm` is the authoritative flag set from the LLM config's
# `isMultimodal` field — NOT a substring match against the model name, which
# misses GPT-5, Gemini 2.x, Ollama VLMs, etc.
...
if not self.state.get("supports_multipart_tool_result", True):
    self.state.setdefault("pending_tool_images", []).extend(collected_images)
return [TextPart(text=text_output), *image_parts]
# comment: only stash a fallback copy when the transport actually needs one —
# native-multipart models already get the images via the return above, so
# retaining them here regardless would just leak memory across turns.
```
(:509–514, :721–728.) The executor copies `ToolOutput.data` straight into a multipart ToolMessage; Ollama-style transports strip images at format time and `shape_retrieved_image_injection` re-injects them via UserMessage FROM THE STASH.

**Flow:** build_message_content_array collects images under the shared ImageBudget → budget exhausted ⇒ degrade to text reference (no Part) → multimodal flag false ⇒ text-only always → both true ⇒ multipart return AND stash only when transport lacks native multipart support.
**Invariant:** (1) Capability comes from an explicit config flag, never model-name sniffing. (2) The fallback stash and the multipart return are ALTERNATIVES keyed on `supports_multipart_tool_result` (default True) — writing both leaks memory turn over turn. (3) ImageBudget is conversation-scoped on state (`setdefault`) so a 50-image cap spans all tools in the turn. (4) A text-only LLM must never receive an ImagePart.
**Probe:** EXECUTED at pin: test_retrieval_extended.py::TestSearchImageMultipart ×4 (:336–462) — real build_message_content_array end-to-end: multipart list returned + NO stash by default (:375), stash written when supports_multipart_tool_result=False (:405), plain str + no stash for text-only (:429–430), exhausted budget degrades to str (:461–462); TestMultimodalLLMFlag :241–273 pins flag-not-name (a mock named gpt-4o stays non-multimodal).
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*agents/actions/test_retrieval*` query="multimodal llm image result returns multipart output pending tool images stash" → resolves test_retrieval_extended.py multimodal-detection classes (graph offsets STALE vs HEAD for this metadata_changed file — decisive ranges cited from direct read; source wins).

## Verdict
Adopt flag-gated multipart returns with an either/or fallback stash for any tool that can emit binary content to LLMs. Adapt the capability flag source and stash key to your transport layer. Omit the budget object only if your framework already caps media per conversation globally.

<!-- capsule-evidence: pipeshub-ai@68509725e15c retrieval.py L509–514/L703–728; test_retrieval_extended.py TestSearchImageMultipart/TestMultimodalLLMFlag (direct read; graph offsets stale); live search_graph 2026-08-26 -->
