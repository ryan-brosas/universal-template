<!-- capsule-v2 -->
# Rerank signal composition — which boosts are multiplicative ≥1 (never filters) and how are path priors, definition lines, and experimental multipliers layered?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** In what order do ranking signals compose so that a wrong signal can reorder but never remove results?

## Per-path facts + per-result composition
**Path/Symbol:** `src/explore.zig` (`rerankAndFinalize` :4963–5160, `PathRerankFacts` :5166–5185, `pathRerankFacts` :5199–5257, `scoreDescBits` :5191–5197).
**Signature:** score = `countOccurrences(line, query)` then: cap 2.0 if tooling; `+5.0` def-line match; `+add_boost`; `×0.6 test / ×0.6 example / ×0.5 tooling / ×0.4 vendor`; docs `min(score,1)*0.5` (any code hit outranks any doc hit); `×gd ×cc ×lfp_mult ×sp_mult`.
**Data Shape:** `PathRerankFacts{defines, def_lines[16], def_overflow, is_tooling/test/example/vendor/doc, add_boost, gd, cc, lfp_mult, sp_mult, path_rank}` computed ONCE per unique path (results arrive file-grouped → consecutive-path memoization).

### Decisive source
```zig
// The boost multipliers ... are ALWAYS a multiplier >= 1, never a filter,
// so a misresolved edge can only nudge a central file up, never drop a real
// result.
fn centralityBoost(...) f32 { const alpha: f32 = 0.15; return 1.0 + alpha * @log(1.0 + c); }
fn graphDistanceBoost(...): BFS over adj+radj from name-matched nodes, max_hops=3;
    return 1.0 + gamma(0.5) / (1 << dist);        // ×1.5, ×1.25, ×1.125, ×1.0625
fn coChangeBoost(...): best shared-commit count among seed files' partners;
    noise floor 2, saturates at 8: 1.0 + 0.25 * min(best/8, 1);
```
Path-name boosts (`pathRerankFacts`): basename stem == query `+15`, containment either way `+8`, directory-segment match `+6` (skipped when stem matched). Sort via one precomputed key per result: `(scoreDescBits(score) << 32) | lexicographic_path_rank` with line asc tiebreak — no string compares in the sort loop.
Experimental priors (env-gated): `RvsmSizePrior` `1 + amp·tanh(k·(lines/avg −1)))` doc-files-exempt; `LexFreqPenalty` DEFAULT-ON amp 0.8 linear down-weight of files the query saturates on many lines (dispatchers/registries/changelogs).

**Flow:** tally per-file hit counts (only when lfp enabled) → build graph distances only when the single-token query exactly names a symbol or call_graph exists (#550 gate keeps NL queries off the graph-build path) → compute facts once per path → seeds for co-change = result files that DEFINE the queried symbol (so plain word queries never trigger the one-time `git log --name-only` shell-out) → compose per-result scores → sort by packed keys → append JSON rerank trace (observation only, never affects ranking).
**Invariant:** Additive/multiplicative graph signals are always ≥ 1.0 — they can only PROMOTE; demotion is exclusively the domain of path-class priors and the lexical-frequency penalty. Every kill-switch env var is folded into `rankingEnvFingerprint()` so caches cannot straddle settings.
**Probe:** `src/test_search.zig` "audit: renderPlainSearch fast-path ranks lexical count over canonical basename", "def-first:" pair (defining file above mention-count; definition line before mentions); `grep -n "CODEDB_NO_CENTRALITY\|CODEDB_LEX_FREQ" src/explore.zig`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "rerankAndFinalize", limit: 10 });
```

## Verdict
Adopt the promote-only graph signals vs demote-only priors split and the definition-line +5 eponymy ladder; adapt multiplier constants to your corpus via the env knobs; omit the JSONL rerank trace unless tuning your own ranker.
