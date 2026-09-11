<!-- capsule-v2 -->
# SpanQuery zero-max semantics — when does a numeric filter bound mean "no cap" vs "cap of zero"?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** In a dict-shaped query DSL, how do you distinguish "filter absent" from "filter = 0" for upper-bound counts without making `0` mean unlimited?

## span-query-zero-bound-guards
**Path/Symbol:** `pydantic_evals/pydantic_evals/otel/span_tree.py:` `SpanNode._matches_query` (:283–410 approx; the four guards below), `SpanQuery` TypedDict total=False (:29–90).
**Signature:** `_matches_query(self, query: SpanQuery) -> bool` — recursive predicate evaluator over name/attribute/status/timing/children/descendants/ancestors conditions plus boolean combinators (`not_`, `and_`, `or_`).
**Data Shape:** `query.get('max_child_count')` etc. return `int | None`; guards compare `is not None`, while minimum-style guards keep truthiness (`if (min_child_count := …) and …`) because 0-min is vacuous.

### Decisive source
```python
# BEFORE #6934 (the bug): falsy 0 skipped the guard → max=0 behaved as UNLIMITED
# AFTER:
if (max_child_count := query.get('max_child_count')) is not None and len(self.children) > max_child_count:
    return False
...
if (max_descendant_count := query.get('max_descendant_count')) is not None and len(
    descendants()
) > max_descendant_count:
    return False
...
if (max_depth := query.get('max_depth')) is not None and len(ancestors()) > max_depth:
    return False
```

**Flow:** every UPPER-bound count/depth guard now runs whenever the key is PRESENT, including `0` → leaf/grandchild nodes satisfy `{'max_descendant_count': 0}` / `{'max_depth': 0}` and roots correctly fail them.
**Invariant:** two rules:
1. For OPTIONAL numeric bounds in a total=False query dict, absence is `None`, so the guard must be `is not None`; plain truthiness silently conflates "no cap" with "cap of exactly 0" — the exact inversion of the intended filter.
2. Keep truthiness for MINIMUM bounds: `min_x = 0` imposes nothing, so skipping it is semantically correct. The asymmetry (truthy-min, is-not-None-max) IS the pattern.
Note `max_duration`/`min_duration` (:315–322) already used `is not None` pre-drift — this fix brought the three COUNT/DEPTH guards in line with the timing guards.
**Probe:** `tests/evals/test_otel.py` :215–216 (`grandchild1_node.matches({'max_descendant_count': 0})` + `not root_node.matches({'max_descendant_count': 0})`) and :452–453 (`root_node.matches({'max_depth': 0})`) — suite EXECUTED GREEN in repo `.venv` this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "SpanNode matches max_descendant_count max_depth zero", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the truthy-min / is-not-None-max asymmetry verbatim in ANY dict-shaped query DSL with optional numeric bounds; adapt the condition vocabulary; omit the recursive combinator machinery if your queries stay flat. Caveat: pydantic_evals/otel plane had ZERO prior capsules — this capsule is its entry point; sibling planes (evaluators/reporting) remain unmined.
