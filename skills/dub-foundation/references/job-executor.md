<!-- capsule-v2 -->
# Job executor — one HTTP endpoint that runs every job and decides retryability

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** When a queued-job webhook fires, which failures must be retried by the queue and which must be answered 2xx to stop retries forever?

## POST /api/jobs/process/[jobName]
**Path/Symbol:** `apps/web/app/api/jobs/process/[jobName]/route.ts:POST` (11–106); loaders in `apps/web/lib/jobs/registry.ts:loadJob` (36–52).
**Signature:** `POST(req, { params }): Promise<Response>` wrapped in `withAxiomBodyLog`; `maxDuration = 600`. `loadJob(name): Promise<JobDefinition | undefined>`.
**Data Shape:** request body is the publish envelope `{ name, dispatchedAt, payload }`; response body is a plain string — only the STATUS CODE carries semantics (2xx = done/never-retry, 500 = retry).

### Decisive source
```ts
await verifyQstashSignature({ req, rawBody });          // HMAC via Upstash Receiver; skipped when VERCEL!=="1"
const envelope = jobEnvelopeSchema.safeParse(parsedBody);
if (!envelope.success) return new Response("Invalid job envelope (non-retryable).");   // 200 STOPS retries
if (urlJobName !== envelope.data.name) return new Response(`Job name mismatch... (non-retryable).`);
const job = await loadJob(jobName);
if (!job) return new Response(`Unknown job "${jobName}" (non-retryable).`);
try { await job.execute(envelope.data.payload); }
catch (error) {
  if (error instanceof z.ZodError)                      // bad payload = PERMANENT -> 200, no retry
    return new Response(`Invalid payload ... (non-retryable).`);
  return new Response(`Job "${job.name}" failed.`, { status: 500 });  // transient -> QStash retries
}
```

**Flow:** read raw body text → verify signature → validate envelope → URL/envelope name cross-check → lazy-load handler from a static `import()` registry (`satisfies Record<string, () => Promise<JobDefinition>>`, webpack code-splits each handler; results memoized in `jobCache`, name mismatch throws) → `execute()` re-parses the payload with the job's zod schema before calling `handle` → map errors: ZodError ⇒ 2xx non-retryable; anything else ⇒ 500 retryable.
**Invariant:** the queue's retry behavior is controlled ENTIRELY by the status code — permanently-invalid input must return 2xx or the queue will retry it until budget exhaustion. Registry names are compile-time-checked against handlers, and `loadJob` verifies `job.name === name` at runtime.
**Probe:** direct test absent for this route (vitest suites live under `apps/web/tests/{analytics,webhooks,misc,...}`). Source-grounded probe: `search_graph` resolves `loadJob`; port with your own test that a ZodError payload returns 200 while a thrown Error returns 500.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "loadJob jobLoaders registeredJobNames", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the single-executor-route + static-loader registry, the name-mismatch guard, and the 2xx-vs-500 retryability contract keyed on ZodError; adapt signature verification to your queue's scheme (QStash Receiver here), the registry list per host, and `maxDuration`. Omit the Axiom body-log wrapper and Vercel-only signature skip. Caveat: no direct upstream test for this seam.
