<!-- capsule-v2 -->
# Degree-gated action guards — how does a provider decide "this lead is not eligible for this action" BEFORE touching the browser?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** where is connection-graph state (who-follows-whom, invite pending) enforced so an outreach tool never sends to an already-connected lead or re-sends a pending invite?

## Extractor normalizes graph state → tool guard short-circuits with endWorkflow
**Path/Symbol:** `shared/server/bots/providers/x/extract.person.profile.ts:extractUserData` (:8-36); `shared/server/bots/providers/linkedin/extra.person.profile.ts:extractConnectionTarget` (:1-34); guards `x.provider.ts:followConnection` (:117-124) / `sendMessage` (:163) vs `linkedin.provider.ts:connectionRequest` (:297-304) / `sendMessage` (:508-515).
**Signature:** extractors → `RunEnrichment = Omit<Required<EnrichmentReturn>,'url'> & { degree: number; pending: boolean }` (`bots.interface.ts`); guards read `lead.degree`/`lead.pending`.
**Data Shape:** X degree from `relationship_perspectives`: both=3, following=1, followed-by=2, none=0 (`pending:false` always); LinkedIn degree scraped from `DISTANCE_(\d)` in the RAW payload JSON and pending from a literal `/PENDING/` match over the same JSON — defaulting to degree 1 when absent.

### Decisive source
```ts
// x.provider.ts followConnection — follow only if NOT already 1st-degree either way:
if (lead.degree === 1 || lead.degree === 3) {
  return { delay: 0, repeatJob: false, endWorkflow: true };
}
// linkedin.provider.ts sendMessage — message ONLY confirmed 1st-degree, never pending:
if (lead.degree !== 1 || lead.pending) {
  return { delay: 0, repeatJob: false, endWorkflow: true };
}
```

**Flow:** every browser job starts with `processLead` (raced against logout watcher), which persists the normalized `{firstName, lastName, picture, degree, pending}` onto the lead; each @Tool method then re-checks eligibility FIRST and returns `endWorkflow:true` — meaning "stop this lead's whole workflow" — without any page interaction. The polarity differs by platform semantics: on X, messaging has no degree precondition (DM gate is UI-driven via `sendDMFromProfile`) while following must skip mutuals; on LinkedIn, connection requests skip existing 1st-degree AND pending invites, while messages REQUIRE confirmed 1st-degree.

**Invariant:** `endWorkflow:true` at a guard means terminal-skip for the lead's campaign path, NOT failure — pairing it with `repeatJob:false; delay:0` makes the throttler cancel the parent workflow via `cancelAll` (workflow.throttle.ts :344-346). The extractor defaults matter: LinkedIn `degree` falls back to 1 (optimistic — enables messaging) while X defaults to 0 (pessimistic — requires explicit relationship evidence before any action); porters who normalize both to one default break exactly one platform's funnel. `pending` exists ONLY on LinkedIn extraction (X always `false`).

**Probe:** deterministic pins from repo root: `grep -cF 'degree === 1 || lead.degree === 3' shared/server/bots/providers/x/x.provider.ts` → 1 (:118); `grep -cF 'lead.degree !== 1 || lead.pending' shared/server/bots/providers/linkedin/linkedin.provider.ts` → 1 (:509); `grep -cF 'DISTANCE_' shared/server/bots/providers/linkedin/extra.person.profile.ts` → 2; `grep -nF '200x200' shared/server/bots/providers/x/extract.person.profile.ts` → :14 (avatar upscale `.replace('normal', '200x200')`); `grep -nF '/UserByScreenName/gm' shared/server/bots/providers/x/x.provider.ts` → :43.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "extractUserData degree relationship", limit: 10 });
```

## Verdict
Adopt the shape: normalize relationship state in ONE pure extractor per platform, then enforce per-action preconditions as cheap early returns; adapt the degree encodings to your platform's API; omit nothing behavioral. Coverage caveat: deterministic probes only (no upstream tests).
