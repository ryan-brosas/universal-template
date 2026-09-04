<!-- capsule-v2 -->
# Junk-chunk classifier + dry-run gap rule — how do you drop OCR/PDF garbage chunks without a false positive nuking the only good hit?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Which heuristics identify junk chunks, in what order, and when may dry-run mode still delete?

## Five explicable rules, code-file whitelist, dual-trigger dry-run exception
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:301-388` (`_classify_junk_chunk`), `:588-660` (`_apply_junk_filter`).
**Signature:** `_classify_junk_chunk(text: str, filename: str) -> str | None`; `_apply_junk_filter(results: list[SearchResult], mode: str) -> tuple[list[SearchResult], _JunkFilterStats]`.
**Data Shape:** Reasons: `too_short` (<30 chars), `cid_glyph_run` (≥3 consecutive `/Cxx`-shaped tokens), `cid_glyph_ratio` (≥30% CID tokens, ≥5 tokens), `digit_punct_ratio` (>65% digit/ws/ascii-punct), `low_alpha_ratio` (<25% alphabetic). Stats track `candidates == returned + filtered_count + below_threshold + drain_drops + dedup_collapses`.

### Decisive source
```python
# engine.py:626-637 — the narrow catch is deliberate
# We intentionally narrow the catch to data-shape exceptions
# (AttributeError / TypeError / ValueError). Catching bare Exception
# masks future bugs introduced inside the classifier (a typo'd regex,
# an unimported symbol) — those should fail loudly so a silent quality
# regression is impossible.
except (AttributeError, TypeError, ValueError) as exc:
    ... reason = None   # keep the chunk
```
Rule ORDER is load-bearing: CID rules run BEFORE the code-file whitelist (no legit `.py` contains `/Cxx` runs), and the RUN rule (more specific) precedes the RATIO rule (catches scattered-CID chunks that dilute the ratio — production trace: Hebrew insurance PDF whose glyph garbage was flooded out by trailing prose). The two ratio rules are DISABLED for code/markup extensions (punctuation density is normal there). Dry-run normally keeps flagged chunks (observation window before enforcing), EXCEPT the dual-trigger gap rule: `mode=="dry_run" and top_score >= 0.3 and r.score < 0.5 * top_score` ⇒ drop anyway with reason suffixed `+low_relative_score`, so "1 high-quality hit + 15 noise" gets caught without flipping the global knob.

**Flow:** classify per chunk (first matching reason wins; None ⇒ keep) → stats counted → `off`: keep all; `dry_run`: keep unless gap-rule fired; `enforce`: drop flagged. Classifier failure on malformed data degrades THAT chunk to keep, never the search.
**Invariant:** A single bad row must never 500 the search, but the catch stays narrow so classifier bugs stay loud; every drop carries a grep-able human-readable reason.

**Probe:** `tests/unit/test_knowledge_rag_scope_failure_fix.py` — pins `cid_glyph_run` firing (:83), code-file whitelist (:96), and the dry-run dual-trigger drop (:106 area).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "classify_junk_chunk apply_junk_filter cid glyph", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered five-rule classifier, extension whitelist, narrow-catch degrade-to-keep, and the dry-run+gap dual trigger. Adapt thresholds to your corpus. Omit CID rules if you never ingest scanned PDFs.
