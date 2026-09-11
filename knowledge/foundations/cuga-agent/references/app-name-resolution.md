<!-- capsule-v2 -->
# TaskAnalyzer app resolution — LLM name suggestions hardened by strict typo correction before any registry lookup

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** An LLM picks which connected apps match a user intent, but it hallucinates near-miss names ("gitlab2" for "gitlab"). How do you accept confident corrections and REJECT ambiguous ones — so a wrong guess never silently routes the task to the wrong app's tools?

## The resolver
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/analyze_task.py` (`TaskAnalyzer.resolve_relevant_apps` :50-103, `match_apps` :106-173, single-app fast path :128-140, forced apps :142-152); `task_analyzer_agent/tasks/app_matcher.py` (`match_apps_for_intent` chain).
**Signature:** `resolve_relevant_apps(requested: List[str], available: List[AppDefinition], typo_match_cutoff=0.8, max_typo_length_delta=2, min_typo_score_margin=0.05) -> List[str]`.
**Data Shape:** `AppMatch {thoughts: str, relevant_apps: List[str]}` from the matcher chain; output is canonical app names in requested order (deduped).

### Decisive source
```python
# analyze_task.py:83-98 — correct only when ONE winner is clearly ahead
scored_matches.sort(key=lambda item: item[0], reverse=True)
if scored_matches:
    best_score, best_match = scored_matches[0]
    close_top_matches = [
        known_lower for score, known_lower in scored_matches
        if best_score - score < min_typo_score_margin   # 0.05
    ]
    if len(close_top_matches) > 1:
        continue          # AMBIGUOUS: drop rather than guess
    corrected = by_lower_name[best_match]
    logger.warning(f"Correcting unmatched app '{normalized}' to closest known app '{corrected}'")
```
Guards around it: candidates pre-filtered by `abs(len(known)-len(normalized)) > max_typo_length_delta` (cheap length gate), scored with `SequenceMatcher(...).ratio() >= typo_match_cutoff` (0.8); exact case-insensitive matches short-circuit; unmatched names are dropped with a warning — never passed through.

**Flow:** `match_apps` per mode: single-connected-app fast paths return WITHOUT an LLM call; `forced_apps` settings bypass matching entirely; otherwise matcher-chain output flows into `resolve_relevant_apps`, then each resolved name re-looks-up its full AppDefinition (unresolved names skipped). The analyzer node runs this BEFORE decomposition; a zero-match result produces a helpful no-match final answer listing connected apps instead of a doomed plan.
**Invariant:** ambiguity is fail-safe by design — when two known apps are within the score margin of the best, the requested name is DROPPED, not guessed (a mis-route sends the whole task to the wrong tool surface; a drop surfaces as user-visible "no match"). Corrections are logged as warnings so silent drift is observable. Dedup happens on canonical names, preserving first-requested order.

**Probe:** direct tests `tests/unit/test_task_analyzer_app_matching.py::test_resolve_relevant_apps_skips_ambiguous_top_fuzzy_matches` (:52), `::test_resolve_relevant_apps_corrects_when_clear_top_fuzzy_winner_exists` (:61), `::test_resolve_relevant_apps_respects_length_delta_guard` (:42), `::test_resolve_relevant_apps_drops_similarity_below_cutoff` (:37), `test_match_apps_corrects_simple_typo_from_forced_apps` (:71), `::test_match_apps_single_app_fast_path_is_unchanged` (:137).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "resolve_relevant_apps SequenceMatcher typo_match_cutoff match_apps_for_intent", limit: 10 });
```

## Verdict
Adopt margin-based ambiguity rejection over always-pick-closest fuzzy correction, the cheap length-delta pre-filter, and LLM-free fast paths for trivial registries. Adapt cutoff/margin constants to your name corpus. Omit hybrid web-app appending unless you mix browser+API execution.
