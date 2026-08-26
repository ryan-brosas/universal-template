<!-- capsule-v2 -->
# Review-Merge Confidence Protocol — how do human verdicts overwrite machine extraction without losing provenance?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** When low-confidence fields go to human review, what exactly happens to their values, confidences, and flags when reviewers answer (or don't)?

## Client-side merge with flag surgery + provisional-calibration honesty
**Path/Symbol:** `packages/python/awaithumans/awaitverify/machine.py` — `_merge_review` (:180–236), confidence constants (:52–61), docstring contract (:22–25); result shapes `ExtractionResult.review: PendingReviewInfo | None`.
**Signature:** `_merge_review(result, *, api_key, base, review_wait_seconds) -> ExtractionResult`; poll increments of 25s against a monotonic deadline (default wait 1200s); `_HUMAN_VERIFIED_CONFIDENCE = 0.99`.
**Data Shape:** per-field `ExtractedFieldConfidence{path, confidence, agreement, flags[]}`; flags in play: PENDING_HUMAN_REVIEW / NOT_FOUND / LOW_AGREEMENT / HUMAN_VERIFIED / PROVISIONAL_CALIBRATION.

### Decisive source
```python
deadline = _time.monotonic() + review_wait_seconds
while _time.monotonic() < deadline:
    polled = await poll_task(..., timeout_seconds=_POLL_INCREMENT_SECONDS)
    if polled.status not in _TERMINAL_STATUSES:
        continue
    if polled.status == "completed" and polled.response_json:
        human_values = _json.loads(polled.response_json)
        for path in result.review.fields:
            entry = result.fields.get(path)
            if path in human_values:
                result.data[path] = human_values[path]
            entry.confidence = _HUMAN_VERIFIED_CONFIDENCE
            entry.flags = [f for f in entry.flags
                if f not in ("PENDING_HUMAN_REVIEW","NOT_FOUND","LOW_AGREEMENT")]
            entry.flags.append("HUMAN_VERIFIED")
        result.document_confidence = round(mean(...), 4)
    return result
logger.warning("Human review still pending after %.0fs ... returning machine "
               "values; the listed fields keep PENDING_HUMAN_REVIEW.")
return result
```

**Flow:** POST page image (≤10MB PNG/JPEG, exactly-one-of path/url, exactly-one-of doc_type/schema) → managed backend returns typed result (+review handle when `human_review != "off"`) → SDK long-polls 25s increments → completed: merge reviewer values into `data`, stamp 0.99 confidence, strip three flags, append HUMAN_VERIFIED, recompute document mean → timeout: return machine values with PENDING_HUMAN_REVIEW INTACT.
**Invariant:** reviewer answered ⇒ HUMAN_VERIFIED even if the value itself was unchanged; unmerged paths (not in review.fields or unknown) stay untouched; malformed/non-dict JSON returns machine result silently; calibration docstring: while `calibration.calibrated` is False scores are rank-orderings, "don't build hard thresholds on provisional scores."
**Probe:** `packages/python/tests/awaitverify/test_machine_extraction.py` (:215 review polled and merged, :241 wait-timeout-returns-machine-values, :115/:127 exactly-one guards, :155 envelope ≥2 docs, :185 public exports incl. Await* aliases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "_merge_review extract_document PendingReviewInfo HUMAN_VERIFIED", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt client-side merge (server stays stateless), the flag-surgery table, deadline-vs-increment polling split, and the provisional-calibration disclosure verbatim. Adapt timeouts/wait to your SLA. Omit envelope cross-checks unless you have multi-document consistency needs.
