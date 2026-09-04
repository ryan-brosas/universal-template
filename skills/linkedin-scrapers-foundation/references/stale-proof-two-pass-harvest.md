<!-- capsule-v2 -->
# Stale-proof two-pass listing harvest — how do you collect job IDs from a results page without StaleElementReference killing the sweep?

**Source:** EasyApplyJobsBot CC BY-NC-SA 4.0 (learn-only: patterns + control flow, zero verbatim reuse) `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** what reference discipline lets one page-walk survive DOM re-renders between harvest and badge scan?

## Immediate attr→int extraction, re-found badge pass, set-difference subtraction
**Path/Symbol:** `linkedin.py:Linkedin.linkJobApply` (:166–198); helper `element_exists` (:505–506).
**Signature:** loop body; `element_exists(self, parent: WebElement, by: str, selector: str) -> bool`.
**Data Shape:** `offerIds/appliedOfferIds: list[int]` from `data-occludable-job-id` split(":")[-1]; badge probe `.//*[contains(text(), 'Applied')]`.

### Decisive source
```python
# Extract all offer IDs immediately to avoid stale element references
offerId = offer.get_attribute("data-occludable-job-id")
if offerId:
    offerIds.append(int(offerId.split(":")[-1]))
...
offersPerPage = self.driver.find_elements(By.XPATH, '//li[@data-occludable-job-id]')  # RE-FIND
if self.element_exists(offer, By.XPATH, ".//*[contains(text(), 'Applied')]"):
    ...
offerIds = [jobId for jobId in offerIds if jobId not in appliedOfferIds]
```

**Flow:** pass 1 walks fresh `//li[@data-occludable-job-id]` rows and converts attrs to plain ints IMMEDIATELY (per-row try/except continue) → jitter sleep → pass 2 RE-FINDS the row elements (old handles are stale by then) and probes each for an Applied-badge descendant via parent-scoped `element_exists` (`len(parent.find_elements)>0`) → set-difference removes applied ids BEFORE any detail-page visit.
**Invariant:** no element reference survives across a navigation; the only long-lived harvest state is a list of ints; if the badge pass fails entirely (outer try), the run degrades to re-visiting applied jobs — never to skipping fresh ones.
**Probe:** `grep -n "data-occludable-job-id" linkedin.py` ⇒ find_elements at :166 AND :184, attr reads :172/:189 (two passes pinned); `sed -n '505,506p' linkedin.py` pins the len>0 helper byte-for-byte.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "linkJobApply applied jobIds", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "EasyApplyJobsBot", qualified_name: "EasyApplyJobsBot.linkedin.Linkedin.linkJobApply" });
```

## Verdict
Adopt: immediate scalarization + re-find second pass + parent-scoped existence probe. Adapt: badge text per locale, id grammar per host. Omit: nothing. Cross-refs: `dedupe-applied-tracking` owns the CROSS-RUN state layer above this DOM sweep; `na-preserving-row-extraction` re-finds rows by index after scroll — same staleness instinct. Coverage caveat: no tests; two-find_elements grep pin + graph parity.
