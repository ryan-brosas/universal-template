<!-- capsule-v2 -->
# Warm-browser service contract — how do I serve many scrapes from one browser without leaking memory or relaunching?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** What is the lifetime split between setup(), run(), and close() that lets ONE browser safely serve sequential AND concurrent scrapes?

## Setup once, run many, close deliberately
**Path/Symbol:** `src/index.ts` — `setup` (:212–284), `run` keepAlive branch (:837–851) + catch-path `close` (:859); consumption shapes `src/examples/module.ts` (:9–22), `src/examples/list-of-urls.ts` (:10–24), `src/examples/server.ts` (:12–26).
**Signature:** `setup(): Promise<void>` (launch + immediate login proof, ONCE); `run(profileUrl): Promise<ProfileResult>` per scrape (fresh factory page each call); `close(page?): Promise<void>` at shutdown.
**Data Shape:** `keepAlive` selects end-of-run scope — false: `close(page)` tears down page+browser+process after EVERY run; true: only `page.close()`, browser stays warm. Each run logs under `scraperSessionId = new Date().getTime()` so interleaved/concurrent runs stay attributable in shared output.

### Decisive source
```ts
if (!this.options.keepAlive) {
  statusLog(logSection, 'Not keeping the session alive.')
  await this.close(page)
} else {
  statusLog(logSection, 'Done. Puppeteer is being kept alive in memory.')
  // Only close the current page, we do not need it anymore
  await page.close()
}
...
// list-of-urls.ts — three CONCURRENT runs share the ONE browser via page isolation:
const [someuser, natfriedman, williamhgates] = await Promise.all([
  scraper.run("https://www.linkedin.com/in/someuser/"),
  scraper.run("https://www.linkedin.com/in/natfriedman/"),
  scraper.run("https://www.linkedin.com/in/williamhgates/"),
])
```

**Flow:** constructor validates options → setup() launches once and immediately proves the session → every run() builds its own hardened page from the factory (concurrency needs PAGES, not browsers) → success path consults keepAlive for teardown scope; ANY failure path closes the WHOLE stack before rethrowing → long-lived deployments shut down with an explicit manual close() (module example comments WHY: idle puppeteer keeps consuming memory).
**Invariant:** page isolation is the concurrency unit — no run-owned state lives on the browser between runs; a broken run may NOT leave a half-warm browser behind (the catch path closes everything even in keepAlive mode).
**Probe:** `src/index.test.ts` pins the default option matrix incl. `keepAlive: false`; the lifecycle itself has no automated test — coverage caveat; deterministic shape pin: `grep -n 'keepAlive\|Promise.all' src/index.ts src/examples/*.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "setup close keepAlive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the setup/run/close triad plus per-run page isolation for any service-shaped browser scraper; adapt concurrency policy (this repo caps NOTHING — Promise.all is unbounded trust; add queueing for real fleets); omit the express example's missing error middleware — a thrown run() escapes the GET handler (hazard recorded in the work record). Teardown mechanics: `zombie-browser-teardown.md`; auth liveness: `cookie-session-bootstrap.md`.
