<!-- capsule-v2 -->
# Tagged-thinking splitter — unterminated-tag degradation to plain text

## Source / Question
`pydantic_ai_slim/pydantic_ai/_thinking_part.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Some models inline their reasoning as `<think>…</think>` inside ordinary text instead of a structured part — how do you split content into ThinkingPart/TextPart when the closing tag may never arrive mid-stream? A porter will treat an unclosed tag as an error or drop the tail.

## Path / Symbol
`_thinking_part.py` — `split_content_into_text_and_thinking(content, thinking_tags)` whole file (:6–31).

## Signature
```python
def split_content_into_text_and_thinking(
    content: str, thinking_tags: tuple[str, str]
) -> list[ThinkingPart | TextPart]: ...
```

## Data Shape
Input: one string + (start_tag, end_tag). Output: ordered parts; every character survives. Three regimes per tag occurrence: closed tag → TextPart(before) + ThinkingPart(inside) and continue; UNTERMINATED tag → remaining content becomes a plain TextPart and scanning stops.

### Decisive source (:15–31)
```python
start_index = content.find(start_tag)
while start_index >= 0:
    before_think, content = content[:start_index], content[start_index + len(start_tag):]
    if before_think:
        parts.append(TextPart(content=before_think))
    end_index = content.find(end_tag)
    if end_index >= 0:
        think_content, content = content[:end_index], content[end_index + len(end_tag):]
        parts.append(ThinkingPart(content=think_content))
    else:
        # We lose the `<think>` tag, but it shouldn't matter.
        parts.append(TextPart(content=content))
        content = ''
    start_index = content.find(start_tag)
if content:
    parts.append(TextPart(content=content))
```

**Flow:** find start tag → emit preceding text if non-empty → look for the close: present ⇒ emit ThinkingPart and keep scanning; absent ⇒ degrade the remainder (tag stripped, content kept as TEXT), consume the string, stop loop → trailing remainder becomes a final TextPart. Empty segments are never emitted.

**Invariant:** The function is total — no exception path, no data loss beyond the tag markers themselves. Unterminated reasoning is TEXT (safe for display), never silently treated as completed thinking. Multiple blocks split into alternating parts in order.

**Probe:** `tests/test_thinking_part.py::test_split_content` (:76) parametrized matrix incl. `'foo bar<think>thinking'` → `[TextPart('foo bar'), TextPart('thinking')]` and cross-tag non-matching (`<custom>` tags left intact when scanning for `<think>`).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'split_content_into_text_and_thinking ThinkingPart'
```

## Verdict
**Adopt** the unterminated-degrades-to-text rule for any streamed tag parser (reasoning tags, code fences, tool-call XML). **Adopt** empty-segment suppression. **Omit** the ThinkingPart/TextPart classes themselves (messages.py surface already covered by other capsules).
