<!-- capsule-v2 -->
# Compaction wire-boundary trim — when does a CompactionPart actually cut history for THIS request, and how does the standing prompt survive?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Which compaction part is the real history boundary on the wire, and what must be re-sent from the trimmed prefix so post-compaction requests don't silently lose directives?

## `_trim_messages_before_compaction` + `_compaction_part_is_wire_boundary` + `_standing_prompt_request`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/__init__.py:_trim_messages_before_compaction` (:2004–2063), `_compaction_part_is_wire_boundary` (defined in messages.py:2801–2829), `_standing_prompt_request` (:2066–2091), `_standing_system_prompt_count` (:1984–2001), `STANDING_PROMPT_PLANTED_KEY` (messages.py:1972).
**Signature:** `_trim_messages_before_compaction(messages: list[ModelMessage], system: str, *, requires_encrypted_content: bool = False, standing_prompt_retained: bool = False) -> list[ModelMessage]`; `_standing_prompt_request(prefix: list[ModelMessage], *, include_system_parts: bool = True) -> list[ModelRequest]`.
**Data Shape:** Returns `[*_standing_prompt_request(prefix), replace(boundary_response, parts=parts[part_index:]), *tail]`; idempotent — re-applying to already-trimmed history is a no-op. The boundary predicate takes `(part: CompactionPart, provider_name: str, *, requires_encrypted_content: bool)`.

### Decisive source
```python
# models/__init__.py:2045-2063 — reverse scan; only a same-provider part that carries
# the payload THIS adapter renders counts as the boundary
for message_index in range(len(messages) - 1, -1, -1):
    message = messages[message_index]
    if not isinstance(message, ModelResponse): continue
    for part_index in range(len(message.parts) - 1, -1, -1):
        part = message.parts[part_index]
        if not isinstance(part, CompactionPart) or not _compaction_part_is_wire_boundary(
            part, system, requires_encrypted_content=requires_encrypted_content):
            continue
        tail = [replace(message, parts=message.parts[part_index:]), *messages[message_index + 1 :]]
        retained = standing_prompt_retained and bool(
            part.provider_details and part.provider_details.get(STANDING_PROMPT_PLANTED_KEY))
        return [*_standing_prompt_request(messages[:message_index],
                                          include_system_parts=not retained), *tail]

# messages.py:2825-2829 — provider-exact render condition
if part.provider_name != provider_name: return False
if part.provider_details and 'encrypted_content' in part.provider_details: return True
return not requires_encrypted_content and part.content is not None
```

**Flow:** reverse-scan messages → newest same-provider CompactionPart that still carries its renderable payload (`encrypted_content` for OpenAI Responses mode, or readable `content`) → split there → rebuild the prefix's standing prompt as its own leading `ModelRequest` (opening `SystemPromptPart`s from the FIRST request wherever it appears, sliced by opening-parts count; latest prefix instructions otherwise) → prepend it unless `standing_prompt_retained` AND the part is stamped `STANDING_PROMPT_PLANTED_KEY`.

**Invariant:** A part is only ever a boundary for the provider that produced it — compaction round-trips to its own provider. A part carrying neither payload is a failed compaction and a boundary for nobody. `requires_encrypted_content` is the CALLER's own render condition, passed per-request, never derived from `provider_name` (one adapter serves many names — Azure reports `'azure'`). Retention (`True`) is honored ONLY for a self-stamped planted item: externally supplied or spliced histories get the standing prompt re-inserted. Retention is also single-hop — re-compaction passes `False` to plant explicitly again. On Anthropic, keeping an original first user message whose `tool_result`'s `tool_use` was trimmed away can 400 (validation runs even on ignored content), which is why the whole prefix goes. Position defines "standing": one `SystemPromptPart` after a user prompt got there later and must NOT hoist — hoisting it would rewrite the first cache section of every later request.

**Probe:** `tests/test_messages.py::test_post_compaction_window_returns_history_unchanged_without_compaction` (:2766) + `test_post_compaction_window_slices_at_the_latest_compaction_part` (:2779) pin the window rule; `tests/test_ag_ui.py:7838` pins that a compaction part acts as the `post_compaction_window` visibility boundary resetting derived state like tool discovery; `tests/test_sanitize_messages.py::test_sanitize_messages_strips_compaction_provenance_stamp` (:103) pins that client-supplied items are never trusted as planted.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_trim_messages_before_compaction _compaction_part_is_wire_boundary _standing_prompt_request STANDING_PROMPT_PLANTED_KEY", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the provider-exact boundary predicate and the standing-prompt rebuild-with-provenance-stamp; adopt the position-based standing-prompt count and the single-hop retention limit. Adapt where the flags are derived (adapter-specific render conditions). Omit the live-verified provider billing notes (Anthropic ignores pre-boundary blocks vs OpenAI bills them) — they motivate, but don't change, the code.
