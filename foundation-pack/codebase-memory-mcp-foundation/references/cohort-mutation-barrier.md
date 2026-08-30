<!-- capsule-v2 -->
# Version cohort mutation barrier — how do you request "everyone finish up" before a destructive upgrade?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What is the quiesce-callback contract for coordinated install/update/uninstall?

## Intent-EX → admission-EX → lifetime probe with prompt callback
**Path/Symbol:** `src/daemon/version_cohort.h:80–95` (`cbm_version_cohort_reserve_for_mutation`) + tests/test_version_cohort.c:309–443.
**Signature:** `cbm_version_cohort_status_t cbm_version_cohort_reserve_for_mutation(manager, deadline_ms, cbm_version_cohort_quiesce_fn quiesce, void *ctx, cbm_version_cohort_quiesce_result_t *out);`
**Data Shape:** Quiesce results: NOT_NEEDED (lifetime already free), REQUESTED, REFUSED (active work untouched), ERROR. The callback fires only AFTER holding the admission lock and observing active lifetime participants; it must return PROMPTLY — the barrier bounds only its native lock wait.

### Decisive source
```c
/* A mutation barrier invokes its quiesce callback only after retaining the
 * admission lock and observing active lifetime participants. The callback
 * must return promptly: the barrier itself bounds only its native lock wait.
 * It returns REQUESTED, REFUSED, or ERROR; NOT_NEEDED is reserved for the API
 * output when lifetime was already free. REFUSED leaves active work untouched;
 * ERROR reports an inability to request orderly quiescence. */
```

**Flow:** publish maintenance intent EX → take admission EX (no new participants) → probe lifetime EX: free ⇒ proceed; held ⇒ invoke quiesce (request sessions wind down) → bounded wait for drain → timeout releases ALL guards cleanly (`version_cohort_mutation_timeout_releases_all_guards`).
**Invariant:** Callback promptness is contractual — long work belongs in the drain wait, not the callback; timeout paths must release every acquired guard symmetrically.
**Probe:** `tests/test_version_cohort.c:version_cohort_mutation_intent_fails_new_admission_and_spans_lease`, `version_cohort_mutation_waits_for_every_lifetime_participant`, `version_cohort_mutation_timeout_releases_all_guards`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_version_cohort_reserve_for_mutation", limit: 5 });
```

## Verdict
Adopt intent→admission→probe barriers with prompt quiesce callbacks for fleet-wide maintenance; adapt guard primitives; the four-value quiesce vocabulary is directly reusable.
