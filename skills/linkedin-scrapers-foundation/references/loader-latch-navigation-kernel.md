<!-- capsule-v2 -->
# Loader-latch navigation kernel — how do you navigate a LinkedIn SPA without navigation errors and KNOW when it is ready?

**Source:** linvo-scraper ISC `main@cfbe91080c73`; Codebase Memory `linvo-scraper`. **Question:** which layer owns navigation failures, and what is the readiness contract every action assumes after `gotoUrl`?

## gotoUrl + waitForLoader (+waitForSalesLoader, timer) — swallowed goto behind a two-phase latch
**Path/Symbol:** `lib/helpers/gotoUrl.ts:gotoUrl` (:3–10); `lib/linkedin/linkedin.abstract.service.ts:LinkedinAbstractService.waitForLoader` (:455–467), `.waitForSalesLoader` (:483–496); `lib/helpers/timer.ts:timer/randomIntFromInterval` (:1–11).
**Signature:** `gotoUrl(page, url): Promise<void>` (swallows everything); `waitForLoader(page): Promise<void>`; `timer(num): Promise<true>` resolving after `num ± 1000 ms`.
**Data Shape:** no return values — the pair communicates ONLY through page state; callers invoke `gotoUrl` WITHOUT `await`.

### Decisive source
```ts
export const gotoUrl = async (page: Page, url: string) => {
  try { await page.goto(url, { timeout: 0 }); } catch (err) {}
};
// abstract service:
async waitForLoader(page: Page) {
  try {
    await page.waitForSelector(".initial-load-animation:not(.fade-load)", { visible: true, timeout: 10000 });
    await page.waitForSelector(".initial-load-animation.fade-load", { timeout: 0 }); // UNBOUNDED fade wait
  } catch (err) {}
  await timer(3000);
}
export const timer = (num: number) => new Promise(res =>
  setTimeout(() => res(true), num + randomIntFromInterval(-1000, 1000)));
```

**Flow:** fire-and-forget goto (timeout ∞, errors void) runs concurrently while the action immediately latches readiness: spinner class appears WITHOUT `fade-load` (≤10 s), then waits UNBOUNDED for `fade-load` to appear, then a jittered fixed settle (3 s ±1 s). Sales pages swap in a harsher ladder: 60 s visible latch then up-to-300 s wait for `.initial-loading-state.hide-loading`.
**Invariant:** navigation errors can NEVER crash an action — the latch layer owns readiness, so a failed/slow goto surfaces as a latch timeout instead of an unhandled promise; the two-phase class flip (present → fading) is the ONLY reliable "SPA finished mounting" signal; ALL sleeps are jittered by construction because every delay goes through `timer()` — no bare `setTimeout` in services.
**Probe:** no upstream tests (blocker). Deterministic anchors: swallowing catch + `timeout: 0` fade wait + jitter formula at HEAD — verification.md probe P6.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "waitForLoader initial-load-animation", limit: 5 });
```
Resolves `LinkedinAbstractService.waitForLoader` :455–467 (+ loadCursor twin hit).

## Verdict
Adopt the ownership split (navigation layer swallows, latch layer decides readiness) and jitter-by-default timing; adapt the specific animation selectors (they rot) to your host's loader markers; omit the infinite `timeout: 0` fade wait if your scheduler needs bounded actions — replace with a large finite cap, not with removing the phase.
