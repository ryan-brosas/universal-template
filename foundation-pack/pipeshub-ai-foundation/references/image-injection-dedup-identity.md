<!-- capsule-v2 -->
# Image injection dedup identity — how do attachment images and tool-sourced images reach the model exactly once across producers?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** two PRE_MODEL hooks inject images into the same first UserMessage (attachments every call; tool results per-call via pop) — what keeps a batch from being dropped or doubled?

## Producer-independent identity + pop-don't-peek delivery
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/attachment_resolver.py:549-640` — `_image_identity` :549, `_inject_into_first_user_message` :563-598 (shared), `shape_image_injection` :511 (L0), `shape_retrieved_image_injection` :601 (L0.1 fallback).
**Signature:** `_image_identity(part) -> str | None`; `_inject_into_first_user_message(messages, parts, text_part_cls, user_message_cls)`; both middleware factories close over per-request AgentContext.
**Data Shape:** LangChain `{"type":"image_url","image_url":{"url":...}}` dicts in `context.attachment_image_blocks` / popped from `context.tool_state["pending_tool_images"]`; converted to ImagePart; first UserMessage content str→[TextPart,*parts] or list→[*content,*new_parts].

### Decisive source
```python
# Key on the normalised data URL rather than `source.data`: the
# same image can arrive as a base64 source or a url source
# depending on which producer built the part, and those two
# carry different `data` strings for identical bytes.
existing_sources = {
    _image_identity(p) for p in content
    if getattr(p, "type", None) == "image"
}
new_parts = [p for p in parts if _image_identity(p) not in existing_sources]
```

**Flow:** L0 converts stored image blocks to parts ONCE (closure cache) and injects into first UserMessage every dispatch; L0.1 POPS `pending_tool_images` each call (retrieval/citations repopulate fresh per tool call — each batch delivered exactly once, on the next model call after production); shared injector dedups per-image by normalized data URL. L0.1 is registered ONLY when `supports_multipart_tool_result` is False (Ollama strips ToolMessage images) so OpenAI/Anthropic never see an image twice (`factory.py:860-867`, flag stashed at :824).
**Invariant:** dedup must be PER-IMAGE on producer-independent identity — "any image present ⇒ skip" drops whole newly-popped batches whenever the message already carried an unrelated image, and a dropped popped batch is gone for good. The deferred check (`if not _cached_parts and context.attachment_image_blocks`) exists because hook wiring runs before the factory populates the blocks.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_attachment_resolver.py::test_populates_citation_maps` (:206) plus factory wiring assertions in `tests/unit/agents/adapter/test_factory_wiring.py::test_hooks_registered_on_all_expected_events` :110. Execute: `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_attachment_resolver.py tests/unit/agents/adapter/test_factory_wiring.py -q` (all passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "shape_retrieved_image_injection pending_tool_images UserMessage injection", limit: 4, fields: ["signature", "name", "file"] });
// resolves attachment_resolver.py symbol cluster line-exact
```

## Verdict
Adopt identity-keyed per-image dedup + pop-based one-shot delivery for multi-producer multimodal injection; adopt capability-gated registration of the fallback path. Adapt the identity function to your part types. Omit LangChain dict shapes and provider-specific stripping lore beyond the gate rule.
