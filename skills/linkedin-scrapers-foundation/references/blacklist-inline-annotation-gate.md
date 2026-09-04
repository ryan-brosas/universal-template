<!-- capsule-v2 -->
# Blacklist inline annotation gate — how can filtering share ONE channel with logging instead of maintaining separate filter state?

**Source:** EasyApplyJobsBot CC BY-NC-SA 4.0 (learn-only: patterns + control flow, zero verbatim reuse) `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** where does the skip decision live if the ledger row itself must explain every skip?

## Annotate-row-then-substring-gate (with an upstream title-vs-detail bug trap)
**Path/Symbol:** `linkedin.py:Linkedin.getJobProperties` (:317–356); orchestrator gate `linkJobApply` (:208).
**Signature:** `getJobProperties(self, count: int) -> str` returning `"{count} | {title} | {detail}{location}"`.
**Data Shape:** config.blackListTitles / config.blacklistCompanies string lists; annotation suffixes "(blacklisted title: …)" / "(blacklisted company: …)".

### Decisive source
```python
res = [blItem for blItem in config.blackListTitles if (blItem.lower() in jobTitle.lower())]
if (len(res) > 0):
    jobTitle += "(blacklisted title: " + ' '.join(res) + ")"
...
res = [blItem for blItem in config.blacklistCompanies if (blItem.lower() in jobTitle.lower())]  # :335 BUG
if (len(res) > 0):
    jobDetail += "(blacklisted company: " + ' '.join(res) + ")"
...
if "blacklisted" in jobProperties:   # :208 gate
```

**Flow:** scrape title → annotate matches INTO the row text → scrape detail → annotate company matches → orchestrator gates the entire visit pipeline on substring `"blacklisted" in jobProperties`; the SAME string is what gets written to the ledger on a hit.
**Invariant:** one string channel serves filter + ledger + counters; annotation preserves the underlying row data (still human-readable). UPSTREAM BUG TRAP at :335: the company list is tested against `jobTitle.lower()` inside the jobDetail block — company blacklisting effectively matches TITLES only; never copy this predicate into a port.
**Probe:** `grep -n '"blacklisted" in jobProperties\|blacklistCompanies if\|blackListTitles if' linkedin.py` ⇒ :208/:324/:335 — gate and both predicates pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "getJobProperties blacklisted jobDetail", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "EasyApplyJobsBot", qualified_name: "EasyApplyJobsBot.linkedin.Linkedin.getJobProperties" });
```

## Verdict
Adopt: annotate-row-then-substring-gate when you want single-channel pipelines whose audit trail explains skips. Adapt: fix the :335 predicate to test jobDetail; consider typed skip reasons once volumes grow. Omit: the bug itself (documented deliberately). Cross-ref: `string-outcome-channel` generalizes the one-decision-point vocabulary; `qa-memory-ladder` shows the loud-sentinel alternative. Coverage caveat: no tests; three-point grep pin + graph parity.
