<!-- capsule-v2 -->
# QStash signature gate — raw-body HMAC verification with a dev bypass

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** How do you verify a signed webhook (queue callback) in a serverless route without breaking local development?

## verifyQstashSignature
**Path/Symbol:** `apps/web/lib/cron/verify-qstash.ts:verifyQstashSignature` (10–49).
**Signature:** `verifyQstashSignature({ req: Request, rawBody: string }): Promise<void>` — throws `DubApiError` (`bad_request` / `unauthorized`) on failure; resolves silently on success.
**Data Shape:** the body MUST be the RAW text (pre-JSON-parse) — signing covers exact bytes, so verifying against re-serialized JSON fails. Signature travels in the `Upstash-Signature` header; optional `upstash-region` header forwards for multi-region.

### Decisive source
```ts
if (process.env.VERCEL !== "1") return;              // dev/local bypass — verification only in prod
const signature = req.headers.get("Upstash-Signature");
if (!signature) throw new DubApiError({ code: "bad_request",
  message: "Upstash-Signature header is required." });
try {
  isValid = await receiver.verify({ signature, body: rawBody,
    upstashRegion: req.headers.get("upstash-region") ?? undefined });
} catch (error) {
  if (error instanceof SignatureError)
    throw new DubApiError({ code: "unauthorized", message: "Invalid Upstash-Signature header." });
  throw error;                                       // unknown errors keep their identity
}
if (!isValid) throw new DubApiError({ code: "unauthorized", ... });
```

**Flow:** caller reads `await req.clone().text()` BEFORE any JSON parsing and passes both request and raw text → missing header is a 400-class `bad_request`; failed verification is an `unauthorized` — the executor route maps thrown errors through `handleAndReturnErrorResponse`, so a forged job never reaches handler code.
**Invariant:** verify-then-parse ordering (signature checks operate on immutable bytes); the environment bypass is explicit (`VERCEL !== "1"`), not accidental; library-specific error types are translated into the app's standard error class so callers need one catch path.
**Probe:** no direct unit test file. Source-grounded probe: `search_graph` project `dub` resolves `verifyQstashSignature` as the sole callee of the jobs executor's auth step; port with your own test that a tampered body throws before envelope validation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "verifyQstashSignature Receiver SignatureError", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt raw-body-first signature verification, header-missing vs header-invalid status split, explicit env bypass, and error-type translation at the boundary; adapt to your signer (QStash Receiver here → Svix/Stripe-style HMAC elsewhere). Omit multi-region forwarding if single-region. Caveat: no direct upstream test for this seam.
