<!-- capsule-v2 -->
# Alias canonicalizer safety rails — how do you rewrite names in text without corrupting unrelated prose?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How does AliasCanonicalizer make entity names mergeable while guarding against word-like aliases and protected spans?

## AliasCanonicalizer
**Path/Symbol:** `ingestion/src/zep_ingest/transforms/canonicalizer.py:30` (`DEFAULT_RISKY_WORDS`), `:49` (`AliasCanonicalizer`), `:145` (`_check_risky`), `:160` (`apply`), `:178` (`flush_warnings`), `:211` (`_resolve`). Constants: MIN_ALIAS_CHARS=3, MAX_NAME_CHARS=200.
**Signature:** `__init__(aliases, *, mode="rewrite"|"annotate", strict=True, risky_words=DEFAULT_RISKY_WORDS)`; construction raises ConfigurationError on any ambiguous mapping.
**Data Shape:** One scan pattern alternates `_URL|_CODE_SPAN|canonicals|aliases`, literals sorted LONGEST first; boundaries are `(?<!\w)/(?!\w)`, NOT `\b`.

### Decisive source
```python
# (?<!\w)/(?!\w) instead of \b: \b needs a word char on the alias side
# of the boundary, so aliases that start or end with punctuation
# (".NET", "C++") would silently never match.
alias_parts = {a: (rf"(?<!\w){re.escape(a)}(?!\w)" if strict
                   else rf"(?i:(?<!\w){re.escape(a)}(?!\w))") for a in ...}
# One scan over aliases AND protected spans (existing canonical mentions,
# URLs, code spans) ... so an alias that contains its canonical still wins
# over the protection of the bare canonical. URLs/code spans go first.
```

**Flow:** construction validates (dup alias across canonicals raises; alias-that-is-a-canonical-name raises — it would be protected in text and silently kill the alias; risky guard rejects case-insensitive common-word matches and <3-char aliases; empty set opts out explicitly) → apply skips json episodes → single-pass finditer with piecewise rebuild → _resolve protects canonical mentions/URLs/code spans; annotate mode inserts "(also known as X)" once per episode idempotently; per-alias counts flushed into warnings ("runaway alias visible in preview() before any API call").
**Invariant:** The default risky-words guard is ON because "alias 'Will' must not rewrite the modal verb in 'he will go' — and case-sensitivity alone cannot save a word-like alias at sentence start". A porter who drops the longest-first ordering lets an alias's own canonical-substring protection shadow the alias.
**Probe:** `grep -c 'def test' ingestion/tests/test_canonicalizer.py` → 37 incl. `test_bare_canonical_still_protected`, `test_alias_with_canonical_prefix_rewrites`, `test_default_risky_words_exported_and_effective`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "AliasCanonicalizer risky words annotate protected", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt risky-word gate + protected-span scan + lookaround boundaries + per-alias count warnings; adapt DEFAULT_RISKY_WORDS vocabulary to your language/domain; omit Zep-specific metadata plumbing.
