<!-- capsule-v2 -->
|# Scope narrow-or-fallback fan-out — how should an LLM-supplied source filter behave when the model passes wrong, partial, or hallucinated IDs?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** When the model names specific sources to search, how do you honor exact matches, survive hallucinated ids, and decide between one combined search and per-source fan-out?

## Intersect-with-scope (empty ⇒ full scope) + same-type-only fan-out
**Path/Symbol:** `backend/python/app/agents/actions/retrieval/retrieval.py` L335–368, L397–489; `backend/python/app/agents/actions/knowledge_graph/ops/scope.py` `KnowledgeScope.narrow_to` (:48–64), `.to_filter_groups_for_source` (:79–97).
**Signature:** `narrow_to(self, requested: Sequence[str] | None) -> KnowledgeScope`; `to_filter_groups_for_source(self, app_id=None, kb_id=None, *, placeholder_agent=False) -> dict[str, list[str]]`.
**Data Shape:** scope = frozen `(app_ids: tuple, kb_ids: tuple)`; filter_groups = `{"apps": [...], "kb": [...]}`; sentinel `"NO_KB_SELECTED"` isolates a single-app leg from KB mixing.

### Decisive source
```python
# scope.py — the fallback IS the contract:
# - Intersection empty (hallucinated ids) → return self as fallback
#   so the search space is never accidentally empty.
if not requested: return self
new_apps = tuple(a for a in self.app_ids if a in requested_set)
new_kbs  = tuple(k for k in self.kb_ids if k in requested_set)
if not new_apps and not new_kbs: return self

# retrieval.py — fan-out only for explicit ids resolving to >1 SAME-type source:
fan_out_sources = explicit_ids and (len(resolved_apps) > 1 or len(resolved_kbs) > 1)
...
raw_results = await asyncio.gather(*search_tasks, return_exceptions=True)
for raw in raw_results:
    if isinstance(raw, Exception): ...continue          # contained
    status_code = raw.get("status_code", 200)
    if status_code in _RETRIEVAL_ERROR_STATUS_CODES:     # {202,500,503}
        error_status = error_status or status_code; continue
    any_success = True
    search_results.extend(raw.get("searchResults", []))
```
(scope.py :57–63; retrieval.py :401–454.)

**Flow:** base scope = curated session `filters` (placeholder agents use full state apps/kb because their filters are synthetic) → explicit ids? intersect; empty intersection ⇒ FULL base scope → >1 resolved source of one type ⇒ one gather leg per source with sentinel isolation, else ONE combined call so the service can cross-rank → merge legs, first error wins only when nothing succeeded.
**Invariant:** (1) An unresolvable filter degrades to BROADER search, never an empty result set — the model must not be able to zero out its own knowledge access by typo. (2) Fan-out requires explicit ids AND same-type multiplicity; mixed single app+single KB stays combined deliberately. (3) Partial failure is success: merge what came back; only all-legs-failure surfaces an error envelope carrying the FIRST observed status. (4) Per-app legs get `NO_KB_SELECTED` unless placeholder agents (no curated KB side to restrict).
**Probe:** EXECUTED at pin: test_retrieval.py :310–330 (`["app-1","app-999"]` ⇒ filter_groups.apps==["app-1"]), TestMultiIdFanOut :420–468 (2 awaits, per-source groups with NO_KB_SELECTED, limit==50 each); test_retrieval_extended.py :168–184 (all-hallucinated ⇒ full kb scope), :529–568 (placeholder uses state apps/kb).
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` query="KnowledgeScope narrow_to hallucinated ids fallback filter groups fan out per source" → rank-1/2 are the two scope methods; ranks 3–8 the fan-out test classes across retrieval AND knowledge_graph suites.

## Verdict
Adopt intersect-or-widen scope resolution for any model-controlled filter over a permission-scoped space; adopt explicit-ids-only fan-out with per-leg exception containment. Adapt sentinel naming and the same-type fan-out predicate to your source taxonomy. Omit the placeholder-agent escape ONLY if your sessions never carry synthetic filters.

<!-- capsule-evidence: pipeshub-ai@68509725e15c retrieval.py L335–489; scope.py L48–97; three direct test classes; live search_graph 2026-08-26 -->
