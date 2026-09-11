<!-- capsule-v2 -->
# Stripe customer search bridge — how do you search a provider's directory and join it to your own rows without an existence oracle?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When a UI needs to pick a provider-side customer and see which ones already exist in your database, what search-then-join shape keeps the response stable and oracle-free?

## Connected graph-selected seam
**Path/Symbol:** route `apps/web/app/(ee)/api/customers/search-stripe/route.ts:GET` (:10-91) · client factory `apps/web/lib/stripe/index.ts:stripeAppClient` · response schema `StripeCustomerSchema` (lib/zod/schemas/customers.ts :204-212) · settings schema `stripeIntegrationSettingsSchema` (lib/integrations/stripe/schema.ts :4).
**Signature:** `GET /customers/search-stripe?search=<string>` (withWorkspace) → `Array<{id, email, name, country, subscriptions, dubCustomerId}>`.
**Data Shape:** Stripe query: `email~"<search>"` (substring match), limit 100, expand ["data.subscriptions"]. Join: prisma customer.findMany {stripeCustomerId: {in: ids}, projectId: workspace.id} selecting {id, stripeCustomerId}; dubCustomerId = matching local row id ?? null. country = `address?.country ?? null`; subscriptions = `subscriptions?.data.length ?? 0`.

### Decisive source
```ts
// route.ts — same two connection gates as the invoice walker, then provider search:
if (!workspace.stripeConnectId) throw new DubApiError({ code: "bad_request", ... });
const installedStripeIntegration = await prisma.installedIntegration.findFirst({
  where: { projectId: workspace.id, integrationId: STRIPE_INTEGRATION_ID },
  select: { settings: true } });
if (!installedStripeIntegration) throw new DubApiError({ code: "bad_request", ... });
const stripe = stripeAppClient({ mode: stripeIntegrationSettingsSchema.parse(
  installedStripeIntegration.settings || {}).stripeMode });
const { data } = await stripe.customers.search(
  { query: `email~"${search}"`, limit: 100, expand: ["data.subscriptions"] },
  { stripeAccount: workspace.stripeConnectId });
// join to LOCAL rows — presence in your DB, not existence on Stripe, is the signal:
const existingCustomers = await prisma.customer.findMany({
  where: { stripeCustomerId: { in: data.map((c) => c.id) }, projectId: workspace.id },
  select: { id: true, stripeCustomerId: true } });
const stripeCustomers = StripeCustomerSchema.array().parse(data.map((customer) => ({
  id: customer.id, email: customer.email, name: customer.name,
  country: customer.address?.country ?? null,
  subscriptions: customer.subscriptions?.data.length ?? 0,
  dubCustomerId: existingCustomers.find((c) => c.stripeCustomerId === customer.id)?.id ?? null,
})));
```
**Flow:** GET with ?search= → zod parse of the single param → two connection gates (workspace.stripeConnectId, installedIntegration row) → mode-resolved app client → provider directory search (email substring, 100 rows, subscriptions expanded) under the connected account → one local findMany keyed by the returned provider ids → per-row projection with null-safe defaults → strict array schema parse → JSON.
**Invariant:** (1) The join direction is provider→local: the response marks which Stripe customers ALREADY have a dub row (dubCustomerId) — absence is a normal value (null), not an error, so the picker never leaks whether an email exists locally before selection. (2) The local join is workspace-scoped (projectId) — the same Stripe customer under two workspaces resolves independently. (3) Every optional provider field gets an explicit null/0 default at the projection boundary (address?.country ?? null, subscriptions?.data.length ?? 0) and the strict schema parse is the last step — provider shape drift dies at the boundary, not in the client. (4) The search grammar is provider-native (`email~"..."` substring) with a hard limit 100 — no client-side filtering of a larger fetch. (5) Mode resolution and the connected-account header are identical to the invoice walker — the two routes are one posture, two reads.
**Probe:** No direct test (grep apps/web/tests/ for search-stripe = ∅). Deterministic probes executed at pin: `email~` query :55; limit:100 + expand data.subscriptions :56-57; existingCustomers findMany :64-71; dubCustomerId join :84-85; StripeCustomerSchema.array().parse :77; connection gates :16-45; NEGATIVE probe: no existence oracle — a miss yields dubCustomerId:null in-band, never a thrown not_found; StripeCustomerSchema fields exactly {id,email,name,country,subscriptions,dubCustomerId} (customers.ts :204-212).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "search-stripe customers email~ dubCustomerId subscriptions", limit: 10 }); // rank-1 expected: customers/search-stripe/route.ts
```

## Verdict
Adopt the search-then-join bridge for any provider-directory picker: return provider rows enriched with a nullable local-id join instead of erroring on unknown rows — the UI gets one stable list and the API leaks nothing about local existence. Adopt null-safe projection defaults plus a strict parse at the boundary to absorb provider shape drift. Adapt the provider-native query grammar and page limit to your provider. Omit nothing silently: erroring when a provider customer has no local twin turns a picker into an oracle; joining without the workspace scope would cross tenant boundaries.
