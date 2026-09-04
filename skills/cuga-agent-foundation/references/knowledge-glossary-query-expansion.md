<!-- capsule-v2 -->
# Glossary query expansion — how do you lift retrieval recall for cross-language / project-specific terms that a dense embedder can't bridge, without dragging the embedding away from intent?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A dense embedder (fastembed all-MiniLM-L6-v2) can't match a query token to a synonym or project code that isn't in its training distribution — how does the glossary inject extra semantic anchors into the query before embedding, and what caps keep expansion from hurting recall?

## Word-boundary expansion with per-entry + total caps
**Path/Symbol:** `src/cuga/backend/knowledge/query_expansion.py:63-197` (`expand_query_with_glossary`), `:45-60` (`_word_boundary_pattern`, lru_cache), constants `MAX_EXPANSIONS_PER_ENTRY = 5` / `MAX_TOTAL_EXPANSIONS = 12` at `:39-42`.
**Signature:** `expand_query_with_glossary(query: str, glossary: list[dict] | None, *, emit_audit_trace: bool = False, audit_q_idx: int | None = None) -> tuple[str, list[dict]]` returning `(expanded_query, match_log)`.
**Data Shape:** `match_log` = list of `{"matched_via": str, "term": str, "anchors_added": [str]}`. Empty glossary / no matches → `(query, [])` verbatim, never errors on malformed entries (silently skips — they're validated at config-set time). Audit record (when `emit_audit_trace` + trace enabled) = `{"kind":"expansion_audit","q_idx","original_query","aliases_fired","dropped_aliases_count","truncated_at","total_expansions"}`.

### Decisive source
```python
# query_expansion.py:121-152 — match term+aliases, append the OTHER anchors
for n in needles:  # [term] + aliases
    if _word_boundary_pattern(n).search(query):
        matched_via = n; break
if matched_via is None: continue
anchors_for_entry = []
for n in needles:
    if n.casefold() == matched_via.casefold(): continue   # query already has it
    if n.casefold() in seen_anchors: continue
    anchors_for_entry.append(n); seen_anchors.add(n.casefold())
    if len(anchors_for_entry) >= MAX_EXPANSIONS_PER_ENTRY: break
    if expansions_used + len(anchors_for_entry) >= MAX_TOTAL_EXPANSIONS: break
```

**Flow:** For each glossary entry, build the needle set = `[term] + aliases`. Match against the query with a case-insensitive word-boundary regex (`(?<!\w)needle(?!\w)` — `\b` doesn't work for Hebrew/CJK, so lookarounds on non-word neighbors are the cross-script boundary proxy). When a needle matches, append every OTHER needle in the entry (the matched one is already in the query) as extra anchors, deduped case-fold, capped at `MAX_EXPANSIONS_PER_ENTRY` per entry and `MAX_TOTAL_EXPANSIONS` globally. If the total cap silenced entries 4..50 of a 50-entry glossary, emit a single structured log line (`cuga.knowledge.glossary_truncated`) so support can grep it — otherwise operators get zero signal (audit-finding S2). The expanded query = original + space-joined anchors; the match_log rides the search response envelope so operators can confirm the glossary fired.

**Invariant:** Expansion is HEURISTIC, not true hybrid (no BM25 sparse leg). Appending too many aliases shifts the embedding AWAY from useful regions — hence the per-entry cap of 5 and total cap of 12 (empirically >~5 anchors starts dragging intent). Word-boundary matching only — substring matches would over-trigger. The regex cache (`lru_cache(2048)`) is essential: a 50-entry × 10-alias glossary would otherwise recompile ~550 regexes per search (~14ms in the no-match path) — audit-finding S1.

**Probe:** `tests/unit/test_knowledge_client_adaptation.py:794` (`test_matches_canonical_term_and_appends_aliases`), `:802` (`test_matches_alias_and_appends_canonical_plus_other_aliases`), `:809` (`test_case_insensitive_match`), `:814` (`test_word_boundary_prevents_substring_false_positive`), `:820` (`test_word_boundary_works_with_non_ascii`), `:827` (`test_multiple_matches_in_one_query`), `:837` (`test_per_entry_cap_respected`), `:846` (`test_total_cap_respected`), `:857` (`test_dedup_across_entries`), `:1029` (`test_s1_regex_pattern_is_cached`), `:1046` (`test_s2_truncated_glossary_emits_log`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "expand_query_with_glossary _word_boundary_pattern MAX_EXPANSIONS_PER_ENTRY", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the word-boundary expansion with per-entry + total caps, the case-fold dedup, the cached boundary regex (non-ASCII safe), and the truncation log. Adapt the caps to your embedder. Omit the audit-trace sink unless you have a trace emitter. Direct-test coverage is comprehensive (all caps + dedup + boundary + non-ASCII cases).
