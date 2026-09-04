<!-- capsule-v2 -->
# LimitGuard always-on safety net — how does an oversized episode NEVER reach the API?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How is the 10,000-char episode limit enforced invisibly, per data type, without ever yielding the original oversize data?

## LimitGuard
**Path/Symbol:** `ingestion/src/zep_ingest/transforms/limits.py:28` (`LimitGuard`), `:34` (`apply`), `:55` (`include_part`), `:78` (`_split`); constants `types.py:13-14` (`MAX_EPISODE_CHARS=10_000`, `SAFE_EPISODE_CHARS=9_500` — LimitGuard default target with headroom for context prefixes).
**Signature:** `LimitGuard(*, limit=SAFE_EPISODE_CHARS)`; `_split(episode) -> tuple[list[str], DataType]`.
**Data Shape:** Split dispatch by data_type: message→`split_lines`, json→`split_json_top_level` (None ⇒ hard-split as text + warning + type downgrade to "text"), text→`split_text(overlap=0)`. Marker metadata: `part: "i/total"`.

### Decisive source
```python
pieces, output_type = self._split(episode)
# A whitespace run longer than the limit hard-splits into all-blank
# slices; they carry no data and Episode rejects them. Dropping them
# cannot empty the list — every non-whitespace character of a valid
# episode still lands in some piece.
pieces = [piece for piece in pieces if piece.strip()]
total = len(pieces)
if total == 1:
    # Splitting can shrink an over-limit episode into one piece (stripped
    # whitespace, compact JSON re-render) — yield the piece, never the
    # original over-limit data.
    yield replace(episode, data=pieces[0], data_type=output_type)
    continue
```

**Flow:** ≤limit → pass through untouched → else split by type → drop blank pieces → single piece? yield shrunk piece : fan out pieces each carrying `part i/total` metadata (marker omitted-with-warning on caller collision or when metadata already has MAX_METADATA_KEYS=10 keys — caller's domain data always wins over diagnostics).
**Invariant:** Pipeline appends LimitGuard AFTER all user transforms, so users never think about the limit and no transform output can overshoot it. The single-piece case must still yield the PIECE — yielding the original would emit data the API rejects. JSON that cannot split validly is downgraded to text WITH a warning, never silently.
**Probe:** `cd /mnt/hdd/utopia/inspo/external/zep/ingestion && python3 -c "import sys; sys.path.insert(0,'src'); from zep_ingest.transforms.limits import LimitGuard"` (import probe; behavior pinned by `tests/test_limits.py` 18 tests incl. `test_whitespace_padded_text_yields_shrunk_piece_not_original`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "LimitGuard episode limit split part marker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt always-on post-transform guard + per-type dispatch + blank-piece drop + never-yield-oversize-original; adapt limit constant to your API's cap; omit Zep-specific warnings wording.
