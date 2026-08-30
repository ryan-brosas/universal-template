<!-- capsule-v2 -->
# Zombie-browser teardown — why does browser.close() need treeKill(SIGKILL) behind it, and why does the error path close too?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** How do I guarantee no orphaned Chrome survives a scraper process — including on failure paths?

## close(page?) + treeKill guard
**Path/Symbol:** `src/index.ts:LinkedInProfileScraper.close` (:416–460); invoked from `run` success (:837–848), `run` catch (:859), `setup` catch (:278), `createPage` catch (:365–372).
**Signature:** `close(page?: Page): Promise<void>` — optional page close, then `browser.close()`, then `treeKill(browser.process().pid, 'SIGKILL', cb)` when a pid exists.
**Data Shape:** keepAlive=false → `close(page)` tears down page+browser+process after EVERY run; keepAlive=true → only `page.close()` and the browser persists for faster recurring scrapes at higher memory.

### Decisive source
```ts
const browserProcessPid = this.browser.process().pid;
// Completely kill the browser process to prevent zombie processes
// https://docs.browserless.io/blog/2019/03/13/more-observations.html#tip-2-when-you-re-done-kill-it-with-fire
if (browserProcessPid) {
  treeKill(browserProcessPid, 'SIGKILL', (err) => { ... })
}
```

**Flow:** every failure path (launch, page-build, mid-run) calls `close()` in its catch BEFORE rethrowing, so an error never leaks a browser; success path consults `keepAlive` — false kills everything, true closes just the working tab. The pid check matters because `treeKill(pid)` on a dead/gone pid errors loudly instead of silently succeeding.
**Invariant:** `browser.close()` alone is NOT enough — Chrome can leave orphaned child processes that outlive the Node script (the linked browserless write-up is cited in-source as the reason). The SIGKILL pass catches what graceful close misses. Long-lived service deployments pair this with `keepAlive:true`; one-shot scripts use the default false.
**Probe:** no automated teardown test — source-grounded only (the upstream justification link lives in the comment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "close treeKill SIGKILL browser process", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt catch-path `close()` + post-close `treeKill(SIGKILL)` as the standard teardown for ANY spawned-browser automation; it complements the suite's `browser-lifecycle.md` (Playwright rollback semantics) rather than duplicating it — Puppeteer flavor here, ordered-guard lifecycle there. Adapt signal/timing to your host. Omit nothing.
