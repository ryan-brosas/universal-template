<!-- capsule-v2 -->
# Post-return stranded DOM walk — how do I tell which half of linvo's scraper services actually runs, and which cited "scroll ladders" are unreachable at this pin?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** before porting any behavior from the two scraper services (or citing their line numbers), which code is LIVE and which is stranded below an early `return`?

## Dead-tail census — both scrapers ship an unreachable DOM-walk half BELOW a response-plane return
**Path/Symbol:** `linkedin.sales.page.service.ts:LinkedinSalesPageService.pagesTask` (return at :89–116; DEAD :118–197) + `workOnResults` (:222–272, sole call site = dead tail :167) + `scrollTo` (:199–220, reachable only via dead `workOnResults`); `linkedin.page.service.ts:LinkedinPageService.pagesTask` (return at :107–130; DEAD :132–171 + `elements` :6–76 recursion); companion remnant `linkedin.global.page.service.ts:startProcess` (return at :110–113; DEAD Promise.race :115–149).
**Signature:** n/a — this capsule is an executability map, not a callable.
**Data Shape:** each service has exactly TWO planes: a LIVE response/interception plane that returns `{pages, values}` from network payloads, and a LEGACY DOM plane (wheel bursts, `[data-scroll-into-view]` card walks, pagination-button reads) left as statements after `return`.

### Decisive source
```ts
// linkedin.sales.page.service.ts — everything below is UNREACHABLE:
    return {
      pages: paging?.total ? Math.ceil((paging.total > 2500 ? 2500 : paging.total) / 25) : 0,
      values: /* ... projection ... */ || [],
    };                                    // <- :116 LAST executed statement

    const val = await Promise.race([ /* .search-results__no-results-message watcher */ ]); // :118
    // ...
    for (let i = 1; i <= 7; i++) { await page.mouse.wheel({ deltaY: 400 }); await timer(2000); } // :159–165
    const values = await this.workOnResults(page);   // :167 — sole workOnResults call site
// linkedin.page.service.ts mirrors it: return at :107–130, then waitForLoader,
// elements() recursion, whole-body wheel, pagination read — ALL unreachable.
```

**Flow (how to verify, not what runs):** control flow ends at the FIRST return; graph callers confirm stranding — `workOnResults` inbound callers_total = 1 (the dead tail), `scrollTo` inbound = pagesTask-dead-tail + workOnResults, `elements` inbound = pagesTask dead region only. The live entry chain is global.page `startProcess` :104–107 → ternary dispatch to sales/normal `pagesTask`, whose first ~100 lines do all real work.
**Invariant:** at pin `cfbe910`, NO DOM-walk statement in either scraper service executes: no wheel burst, no `[data-scroll-into-view]` relocation, no `.artdeco-pagination__pages` read, no no-results race. Any capsule/probe/test asserting those behaviors as production behavior of THIS repo is wrong-at-pin; they are valid only as historical patterns or as code that upstream could resurrect by deleting the earlier return.
**Census ranges:** sales file — 156 of 273 lines dead (:118–197, :199–220, :222–272); page file — 46 of 173 dead (:132–171) plus `elements` :6–76; global file — 5-line remnant :115–149. Also dead-by-comment elsewhere in the repo: abstract `selectContract` (pass-1 finding). The engagement/connect/endorse uses of `moveMouseAndScroll` ARE live — the primitive survives even though these two call sites don't.
**Probe:** no upstream test runner exists at pin — recorded BLOCK; deterministic anchors executed instead: `grep -n "return {" lib/linkedin/linkedin.sales.page.service.ts` shows the live return at :89 followed by orphan statements; `grep -n "Promise.race" lib/linkedin/linkedin.sales.page.service.ts lib/linkedin/linkedin.global.page.service.ts` pins both remnants (:118 / :115); `sed -n '116p'`-style line checks were done via direct reads of both whole files (273L / 173L).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "linvo-scraper", function_name: "workOnResults", direction: "inbound", depth: 2 });
```

## Verdict
Adopt the audit habit: after ANY refactor-to-interception, grep for statements after your `return` and either delete them or fence them with a named marker, because citation tools and future miners cannot see reachability; adapt nothing here (it is a map, not a pattern); omit porting `workOnResults`/`scrollTo`/`elements` bodies unless upstream revives them — if it does, they become the suite's only full Sales Nav card-walk implementations and deserve fresh capsules. This capsule supersedes humanization-scroll's linvo instance citations (pagesTask wheel :159–165/:168–178, scrollTo :199–220): those lines exist but are DEAD at pin — annotation applied there this pass. Coverage caveat: source-grounded whole-file reads + graph traces; zero upstream tests.
