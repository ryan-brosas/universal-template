<!-- capsule-v2 -->
# Datetime & text utils — UTC normalization, sentence truncation

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how do small datetime/text helpers keep timestamps UTC and truncate at sentence boundaries?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/datetime_utils.py`: `utc_now` (:20), `ensure_utc` (:25), `convert_datetimes_to_strings` (:45); `graphiti_core/utils/text_utils.py`: `truncate_at_sentence` (:29), `concatenate_episodes` (:62).
**Signature:** `ensure_utc(dt)` — converts a datetime to UTC (or None); `convert_datetimes_to_strings(obj)` — recursively converts datetimes to ISO strings; `truncate_at_sentence(text, max_chars)` — truncates at a sentence boundary.
**Data Shape:** datetimes normalized to UTC; truncation at sentence boundary (never mid-sentence); episode concatenation for batched extraction.

### Decisive source
```ts
def ensure_utc(dt): return dt.astimezone(timezone.utc) if dt else None
def truncate_at_sentence(text, max_chars):
    # truncate at the last sentence boundary <= max_chars
def convert_datetimes_to_strings(obj):
    # recursively convert datetime -> isoformat string
```

**Flow:** timestamps are normalized to UTC (never naive/local); datetimes converted to strings for serialization; text truncated at sentence boundaries (so a truncated excerpt is always a complete sentence).
**Invariant:** all timestamps are UTC; truncation never splits a sentence; serialization is timezone-safe.
**Probe:** `tests/` datetime/text tests (ensure_utc converts; convert_datetimes_to_strings recurses; truncate_at_sentence stops at a boundary).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "ensure_utc convert_datetimes_to_strings truncate_at_sentence", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the UTC normalization + sentence-boundary truncation helpers; adapt the truncation limits and serialization format to host.
