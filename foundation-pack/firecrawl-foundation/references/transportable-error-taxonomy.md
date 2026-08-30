<!-- capsule-v2 -->
# Transportable error taxonomy — which errors cross process boundaries and how do they round-trip?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I split user-facing from internal errors so workers can serialize failures back to API responses?

## Transportable error taxonomy
**Path/Symbol:** `apps/api/src/scraper/scrapeURL/error.ts` (721L whole file; ~30 classes) + base in `apps/api/src/lib/error.ts` (`TransportableError`, `ErrorCodes`, `ScrapeJobTimeoutError`).
**Signature:** every transportable class: `constructor(...)` → `super("SCRAPE_<NAME>", <user message>)`; instance `.serialize(): {code, message, stack, ...fields}`; static `.deserialize(code, data): ConcreteError` restoring fields + stack.
**Data Shape:** two families — `extends Error` (INTERNAL loop-control: WrappedEngineError, EngineUnsuccessfulError, WaterfallNextEngineSignal, EngineSnipedError, IndexMissError, FEPageLoadFailed, AddFeatureError/RemoveFeatureError carrying featureFlag arrays) vs `extends TransportableError` (USER-FACING, code-prefixed SCRAPE_*: NoEnginesLeftError w/ fallbackList payload, SSLError w/ skipTlsVerification flag, SiteError w/ errorCode + per-code explanation table, PDFInsufficientTimeError carrying pageCount + computed minTimeout advice, ScrapeRetryLimitError carrying reason + full stats snapshot, ZDRViolationError, AgentIndexOnlyError…).

### Decisive source
```ts
export class NoEnginesLeftError extends TransportableError {
  constructor(fallbackList: Engine[]) {
    const enginesTriedStr = fallbackList.join(", ");
    const message = isSelfHosted()
      ? `All scraping engines failed... Check your server logs...`     // self-host variant
      : `All scraping engines failed... contact us at help@firecrawl.com with your request ID...`;
    super("SCRAPE_ALL_ENGINES_FAILED", message);
    this.fallbackList = fallbackList;
  }
  serialize() { return { ...super.serialize(), fallbackList: this.fallbackList }; }
  static deserialize(_, data) { const x = new NoEnginesLeftError(data.fallbackList); x.stack = data.stack; return x; }
}
```

**Flow:** engines throw either family ⇒ waterfall classifies (internal = swallow/filter, transportable = terminal rethrow) ⇒ top-level scrapeURL catch maps ~20 classes to span attribute `scrape.error_type` and returns `{success:false, error}` ⇒ worker serializes via TransportableError.serialize into the job record ⇒ API deserializes for the client. Self-hosted deployments get different message tails (`isSelfHosted()` branch) — support-contact lines stripped.
**Invariant:** The code string is the wire contract ("SCRAPE_LOCKDOWN_CACHE_MISS" is matched BY STRING in billing :110-114) — renaming a code breaks cross-process matching. Internal control-flow errors must NEVER extend TransportableError or they'd leak to users and skip Sentry's flow-control filter (queue-worker.ts:104-111 "Skip TransportableErrors: they're flow control").
**Probe:** anchored at repo root `apps/api/src`: `grep -c 'extends TransportableError' scraper/scrapeURL/error.ts` → 24; `grep -n 'SCRAPE_ALL_ENGINES_FAILED' scraper/scrapeURL/error.ts` → 1 hit at :43 (def).
**Probe:** anchored at repo root `apps/api/src`: `grep -rn 'SCRAPE_LOCKDOWN_CACHE_MISS' lib/scrape-billing.ts` → exactly 1 hit at :111 (string-matched billing exception).
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "TransportableError serialize deserialize NoEnginesLeftError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-family taxonomy + serialize/deserialize pairs + string-code wire contract for any multi-process job system; adapt codes/messages; omit the self-host message branching unless you ship both distributions.
