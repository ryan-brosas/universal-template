<!-- capsule-v2 -->
# Postback lifecycle API — how are partner postbacks created, capped, channel-detected, and dry-run tested?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What does creating a partner postback guarantee (secret shape, receiver inference, cap), and how does send-test avoid polluting production enrichment?

## partner-profile/postbacks routes: cap → secret mint → hostname-classified receiver → test dispatch
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/postbacks/route.ts:POST` (:44-84); rotate `.../[postbackId]/rotate-secret/route.ts:POST` (:10-34); send-test `.../[postbackId]/send-test/route.ts:POST` (:17-50); channel classifier `apps/web/lib/postback/utils.ts:identifyPostbackChannel` (:5-12); constants `apps/web/lib/postback/constants.ts`.
**Signature:** create input `{name ≤40, url https-only, triggers ≥1}`; output = row + one-time `secret` (`createPostbackOutputSchema`); all routes gated `requiredPermission` + `featureFlag:"postbacks"`.
**Data Shape:** MAX_POSTBACKS=5; POSTBACK_SECRET_PREFIX="pbsec_" length 16 via `createToken`; id `pb_`.

### Decisive source
```ts
if (postbackCount >= MAX_POSTBACKS)
  throw new DubApiError({ code: "exceeded_limit",
    message: `Maximum number of postbacks (${MAX_POSTBACKS}) reached.` });
const secret = createToken({ prefix: POSTBACK_SECRET_LENGTH ? undefined : undefined, ... });
const postback = await prisma.postback.create({ data: { id: createId({ prefix: "pb_" }),
  ..., secret, triggers, receiver: identifyPostbackChannel(url) } });
return NextResponse.json(createPostbackOutputSchema.parse(postback), { status: 201 });
```
(route.ts :54-81 — secret minted :61-63, receiver inferred at CREATE time, never stored-editable)
```ts
const POSTBACK_URL_RECEIVERS: Record<string, "slack" | "custom"> = {
  "hooks.slack.com": "slack" };
export const identifyPostbackChannel = (url: string) => {
  try { const { hostname } = new URL(url);
        return POSTBACK_URL_RECEIVERS[hostname] ?? "custom"; }
  catch { return "custom"; } };                       // invalid URL degrades to custom
```
(utils.ts :1-12)

**Flow:** create: count-cap → mint `pbsec_` secret → persist with hostname-inferred receiver → return the secret EXACTLY ONCE (list endpoints project through `postbackSchema` which omits it) → rotation re-mints and returns the new value without touching anything else. Send-test: event must be in the postback's OWN triggers list (bad_request otherwise) → dispatches a bundled sample payload with `skipEnrichment:true` and `isTest:true`, which the dispatcher honors by including disabledAt-set rows and skipping the enricher registry.
**Invariant:** (1) the URL is validated https-only at the schema layer and its HOSTNAME decides the adapter forever after — changing receiver semantics means rotating the endpoint, not editing a field; (2) secrets are shown once per creation/rotation and never re-serialized by read APIs; (3) tests ride the SAME delivery path as production events except for enrichment + disabled-row inclusion, so test success proves wiring, not payload shape.
**Probe:** deterministic probe: `grep -n 'identifyPostbackChannel(url)' 'apps/web/app/(ee)/api/partner-profile/postbacks/route.ts'` = :74; `grep -c 'skipEnrichment: true' 'apps/web/app/(ee)/api/partner-profile/postbacks/[postbackId]/send-test/route.ts'` = 1. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "identifyPostbackChannel", limit: 5 });
```

## Verdict
Adopt the once-shown secret lifecycle, hostname→receiver classification, and trigger-scoped test dispatch. Adapt caps/prefixes and permission names. Omit the feature-flag gate if your host has no flag service (but keep the route-level permission checks).
