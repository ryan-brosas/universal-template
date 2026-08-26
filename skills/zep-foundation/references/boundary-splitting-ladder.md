<!-- capsule-v2 -->
# Boundary-aware splitting ladder — how does every data type get split without corrupting its shape?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How are oversize text/message/json payloads divided so each piece stays semantically valid?

## _splitting primitives
**Path/Symbol:** `ingestion/src/zep_ingest/transforms/_splitting.py:17` (`hard_split`), `:21` (`_overlap_tail`), `:32` (`_split_long_paragraph`), `:52` (`split_text`), `:78` (`split_lines`), `:98` (`_split_json_value`), `:175` (`_reject_non_finite`), `:182` (`split_json_top_level`).
**Signature:** `split_text(text, chunk_size, overlap=0) -> list[str]`; `split_lines(text, chunk_size)`; `split_json_top_level(text, chunk_size) -> list[str] | None`.
**Data Shape:** Ladder: paragraph (`\n\n`) → sentence (`(?<=[.!?])\s+`) → hard slice. Overlap tail = last N chars rounded FORWARD to the next whitespace (never mid-word).

### Decisive source
```python
def _reject_non_finite(token: str) -> float:
    """NaN/Infinity/-Infinity are a Python extension that json accepts on the
    way in and writes back out, so a body carrying one would split into pieces
    no strict JSON parser accepts — exactly what this module promises not to
    emit."""
    raise ValueError(f"{token} is not valid JSON")

def split_json_top_level(text, chunk_size):
    try:
        parsed = json.loads(text, parse_constant=_reject_non_finite)
    except (json.JSONDecodeError, ValueError):
        return None   # caller falls back to text hard-split
    return _split_json_value(parsed, json.dumps, chunk_size)
```

**Flow:** split_text packs paragraphs up to chunk_size (oversize paragraph → sentence loop; oversize sentence → hard_split); overlap tail re-primes the next chunk only if tail+sentence still fits. split_lines packs whole lines. JSON splitting recurses value-by-value (strings via binary-search on render length; lists/dicts grouped greedily) and returns None when the body isn't JSON — "leaving the caller to split it as text rather than emitting pieces that only look like JSON".
**Invariant:** Every returned JSON piece must re-parse as valid JSON; a never-emitting-partial-lines rule for text (chunks only ever shrink at boundaries). The whitespace-tail rounding prevents overlap from starting mid-word.
**Probe:** `grep -c 'def test' ingestion/tests/test_chunker.py ingestion/tests/test_limits.py | awk -F: '{s+=$2} END{print s}'` → ≥30; e.g. test_limits `test_compact_json_rerender_yields_piece_without_split_warning`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "split_text paragraph sentence hard_split json", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-rung boundary ladder + valid-JSON-piece guarantee + forward-rounded overlap; adapt sizes/tokens to your content domain; omit Zep cookbook defaults.
