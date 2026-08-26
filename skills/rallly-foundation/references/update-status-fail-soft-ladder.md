<!-- capsule-v2 -->
# Update-status fail-soft ladder — how do you ask an update server "is there anything newer?" so a hang, a lie, or an outage can never break the admin UI?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What is the complete set of failure exits, and what keeps a hostile/buggy upstream from surfacing a cross-major release as pullable?

## getUpdateStatus — null on every exit, 3s timeout, within-major double gate
**Path/Symbol:** `apps/web/src/features/instance-settings/service.ts:getUpdateStatus` (lines 23–96); response shape `updateStatusSchema` (lines 11–21, all fields `nullish`); sole caller `loaders.ts:loadUpdateStatus` (lines 8–16, React `cache`-wrapped).
**Signature:** `getUpdateStatus({ instanceId }) → { status: "update-available"; latest; url; publishedAt } | { status: "up-to-date" } | { …same fields…, newMajor: { major, migrationGuideUrl } | null } | null`.
**Data Shape:** upstream payload is schema-checked with every field optional — absence is expected, not exceptional.

### Decisive source
```ts
const res = await fetch(url, {
  // Node fetch has no default timeout — without this a hung upstream
  // holds the streamed slot open indefinitely on a cold cache
  signal: AbortSignal.timeout(3000),
  next: { revalidate: 3600 },
});
if (!res.ok) { logger.warn(…); return null; }
const parsed = updateStatusSchema.safeParse(await res.json());
if (!parsed.success) { logger.warn(…); return null; }

// The endpoint scopes `latest` to our own major. Guard anyway: a release
// from another major must never surface as a pullable update, and this
// code is frozen in fleet binaries.
const withinMajor =
  latest && releaseUrl && publishedAt &&
  currentMajor !== null &&
  getMajorVersion(latest) === currentMajor &&
  isOutdated(appVersion, latest)
    ? { status: "update-available" as const, latest, url: releaseUrl, publishedAt }
    : { status: "up-to-date" as const };
```

**Flow:** env/version precheck (`!appVersion || !env.API_BASE_URL → null`, :24) → fetch with explicit 3s abort + 1h revalidate → non-ok status ⇒ warn+null (:42) → response fails safeParse ⇒ warn+null (:50) → verdict assembly: within-major arm demands the advertised `latest` parse to the CURRENT major AND be strictly older-than-latest per `isOutdated`; the separate `newMajor` arm demands its parsed major be strictly GREATER than current before it survives into the result → any thrown error in the whole try ⇒ warn+null (:94). Four distinct exits, one outcome shape: `null` means "render nothing", never "error".
**Invariant:** this code ships frozen inside self-hosted fleet binaries talking to a server that can be older OR newer than it — so it trusts nothing: no field is required by the schema, no non-ok status throws, and the client-side major guard re-derives trust rather than assuming the endpoint's scoping. Telemetry-only surface: every failure is a `logger.warn` with context (instanceId, version, issues), and the caller (`loadUpdateStatus`) returns null again when `instanceId` is missing.
**Probe:** no dedicated test for service.ts (caveat recorded — network-bound). The comparison primitives beneath it ARE directly tested: `utils.test.ts` whole (52L) pins `getMajorVersion("4foo")→null`, prerelease blindness, and numeric minor ordering. Byte anchors verified by direct read: :24/:34/:35/:42/:50/:59/:67/:72/:94.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "getUpdateStatus loadUpdateStatus withinMajor newMajor", limit: 10 });
```

## Verdict
Adopt the four-exit fail-soft ladder and the explicit AbortSignal for any outbound call that decorates (but must never block) an admin surface; adapt the 3s/1h constants to your UX budget; omit the fleet-frozen rationale if your client updates atomically with the server. The subtle porting trap is treating the endpoint's own major-scoping as sufficient — Rallly deliberately does NOT ("this code is frozen in fleet binaries"): re-validate server claims at the consumer.
