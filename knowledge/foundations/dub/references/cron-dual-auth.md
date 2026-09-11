<!-- capsule-v2 -->
# Cron auth dual-protocol — why does one wrapper verify two different signature schemes, and what does each method trust?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How do cron routes authenticate BOTH Vercel-scheduled GETs and QStash POSTs, and where is verification deliberately skipped?

## withCron: method-keyed verifier + axiom body log
**Path/Symbol:** `apps/web/lib/cron/with-cron.ts:withCron` (:23-70); `apps/web/lib/cron/verify-qstash.ts:verifyQstashSignature` (:8-45); `apps/web/lib/cron/verify-vercel.ts:verifyVercelSignature` (:5-26); qstash clients `apps/web/lib/cron/index.ts:1-20`.
**Signature:** `withCron(handler({req,params,searchParams,rawBody}))`; GET ⇒ Vercel Bearer secret; POST ⇒ Upstash Receiver HMAC; other methods throw.
**Data Shape:** QStash receiver verifies `Upstash-Signature` honoring `upstash-region` for multi-region signatures; Vercel compares `authorization` to `Bearer ${CRON_SECRET}`.

### Decisive source
```ts
if (req.method === "GET") {
  // GET requests are typically from Vercel Cron
  await verifyVercelSignature(req);
} else if (req.method === "POST") {
  // POST requests are typically from QStash
  rawBody = await clonedReq.text();
  await verifyQstashSignature({ req, rawBody });
} else { throw new Error(`Unsupported HTTP method: ${req.method}`); }
```
(with-cron.ts :40-50)
```ts
// skip verification in local development
if (process.env.VERCEL !== "1") return;
...
} catch (error) {
  if (error instanceof SignatureError)
    throw new DubApiError({ code: "unauthorized", message: "Invalid Upstash-Signature header." });
  throw error;
}
```
(verify-qstash.ts :15-38)

**Flow:** wrapper clones the request BEFORE the handler so the raw body survives both the axiom success-log and the verifier → dispatch on method → handlers get `rawBody` and parse it themselves (`inputSchema.parse(JSON.parse(rawBody))`) → errors funnel to Axiom then `logAndRespond(message, {status: ErrorCodes[code]})`. Two qstash client singletons exist: the default injects the Vercel protection-bypass header in previews; `qstashWithoutBypass` exists specifically so third-party webhook deliveries never receive dub's bypass secret. Batch enqueue helper wraps `qstash.batchJSON` with 3 exponential retries then a Slack-mention log+throw; workflow trigger helper adds `retries:5`, default flowControl `{key: workflowType, parallelism:15}`, and per-type correlation logging.
**Invariant:** (1) VERCEL≠1 disables BOTH verifiers — a porter running the app outside Vercel must replace, not delete, this gate or every cron route becomes public; (2) signature verification needs the RAW body string, which is why the clone happens before any parse; (3) the bypass-secret split is a trust boundary: infrastructure bypass credentials must never reach external receivers.
**Probe:** deterministic probe: `grep -c 'process.env.VERCEL !== "1"' apps/web/lib/cron/verify-qstash.ts apps/web/lib/cron/verify-vercel.ts` = 2; `grep -n 'Unsupported HTTP method' apps/web/lib/cron/with-cron.ts` = :49. No upstream unit suite covers these files (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "verifyQstashSignature", limit: 5 });
```

## Verdict
Adopt the method-dispatched dual verifier and the raw-body-before-parse discipline for any serverless route that serves both a scheduler and a queue. Adapt the env gate to your platform's dev signal. Omit the preview-bypass header logic when not hosted on Vercel.
