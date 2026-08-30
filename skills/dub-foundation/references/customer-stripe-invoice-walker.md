<!-- capsule-v2 -->
# Customer Stripe invoice walker — how do you read a connected Stripe account's invoices into your own commission ledger without trusting the connection?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When your app reads invoices from a USER's connected Stripe account (Connect `stripeAccount` header), what gate ladder and mapping keep the read honest about mode, identity, refunds, and your own ledger linkage?

## Connected graph-selected seam
**Path/Symbol:** route `apps/web/app/(ee)/api/customers/[id]/stripe-invoices/route.ts:GET` (:10-39) · kernel `apps/web/lib/api/customers/get-customer-stripe-invoices.ts:getCustomerStripeInvoices` (:25-179) · client factory `apps/web/lib/stripe/index.ts:stripeAppClient` (:12-26) · settings schema `apps/web/lib/integrations/stripe/schema.ts:stripeIntegrationSettingsSchema` (:4) · response schemas `StripeCustomerInvoiceSchema` (lib/zod/schemas/customers.ts :213-220) · program anchor `getDefaultProgramIdOrThrow` (lib/api/programs/get-default-program-id-or-throw.ts :6-16).
**Signature:** `getCustomerStripeInvoices({stripeCustomerId, stripeConnectId, programId}) => Array<{id, amount, createdAt, refunded, dubCommissionId?, metadata}>`; route `GET /customers/[id]/stripe-invoices` (withWorkspace).
**Data Shape:** Constants: invoices.list {customer, status:"paid", limit:100, expand:["data.payments.data.payment"]}; charges.list {limit:100, customer}. Settings: `stripeMode` enum(live|test|sandbox).default("live") — the workspace's installedIntegration row is the ONLY mode source. Secret map: live→STRIPE_APP_SECRET_KEY, test→STRIPE_APP_SECRET_KEY_TEST, sandbox→STRIPE_APP_SECRET_KEY_SANDBOX. Output amount = `total_excluding_tax` when `amount_paid === total && total_excluding_tax != null`, else `amount_paid`.

### Decisive source
```ts
// route gate ladder (route.ts :11-36) — connection, customer, linkage, program:
if (!workspace.stripeConnectId) throw new DubApiError({ code: "bad_request",
  message: "Your workspace isn't connected to Stripe yet. ..." });
const customer = await getCustomerOrThrow({ workspaceId: workspace.id, id: customerId });
if (!customer.stripeCustomerId) throw new DubApiError({ code: "bad_request",
  message: "Customer doesn't have a Stripe customer ID. ..." });
return NextResponse.json(await getCustomerStripeInvoices({
  stripeCustomerId: customer.stripeCustomerId, stripeConnectId: workspace.stripeConnectId,
  programId: getDefaultProgramIdOrThrow(workspace) }));
```
```ts
// kernel (get-customer-stripe-invoices.ts) — mode from the workspace's OWN settings row:
const installedStripeIntegration = await prisma.installedIntegration.findFirst({
  where: { project: { stripeConnectId }, integrationId: STRIPE_INTEGRATION_ID },
  select: { settings: true } });
if (!installedStripeIntegration) throw new Error("Stripe integration is not installed on your workspace.");
const stripeIntegrationSettings = stripeIntegrationSettingsSchema.parse(installedStripeIntegration.settings || {});
if (!stripeCustomerId.startsWith("cus_")) throw new DubApiError({ code: "bad_request",
  message: `Customer has an invalid Stripe customer ID (${stripeCustomerId}). ...` });
const stripe = stripeAppClient({ mode: stripeIntegrationSettings.stripeMode });
// paid-invoice page under the CONNECTED account; resource_missing → actionable 400:
const res = await stripe.invoices.list({ customer: stripeCustomerId, status: "paid", limit: 100,
  expand: ["data.payments.data.payment"] }, { stripeAccount: stripeConnectId });
// charges fetch is BEST-EFFORT (older integrations lack charges.read):
try { charges = (await stripe.charges.list({ limit: 100, customer: stripeCustomerId },
  { stripeAccount: stripeConnectId })).data; } catch (error) { console.warn(error); }
// refund detection = payments expand joined to the charges page by payment_intent:
if (payment.payment?.type === "payment_intent" && payment.payment?.payment_intent) {
  const charge = charges.find((c) => c.payment_intent === payment.payment?.payment_intent);
  if (charge?.refunded || (charge?.amount_refunded ?? 0) > 0) return { refunded: true, metadata: rest };
}
// ledger linkage: invoiceId → dub commission id (program-scoped):
const commissions = await prisma.commission.findMany({
  where: { invoiceId: { in: invoices.map((i) => i.id) }, programId },
```
**Flow:** GET route → withWorkspace auth → four-gate ladder (connect id, customer-or-throw, customer linkage, default program) → kernel loads the workspace's installedIntegration row and parses stripeMode (default live) → validates the cus_ prefix → builds the app client for that mode → one paid-invoice page (limit 100, payments expanded) under the connected account → best-effort charges page → program-scoped commission lookup builds the invoiceId→commissionId map → per-invoice refund probe (payments × charges join on payment_intent) → StripeCustomerInvoiceSchema.parse per row.
**Invariant:** (1) The mode is the workspace's OWN stored integration setting (default "live"), and the client secret is selected from a per-mode env map — a test-mode connection can never silently read through the live key. (2) Every Stripe call carries `{ stripeAccount: stripeConnectId }` — the read executes on the connected account, never the platform's own. (3) The charges read is best-effort by design: a missing charges.read permission degrades refund detection to `refunded:false` (console.warn) instead of failing the whole invoice read. (4) `resource_missing` is translated from a Stripe error into an actionable bad_request telling the user to fix the customer's stored ID — stale linkage is a user-data problem, not a 500. (5) Refund truth is DERIVED, not stored: the invoice row carries no refund flag; it is computed per read from the payments expand joined to the charges page by payment_intent. (6) The dubCommissionId join is program-scoped — the same Stripe invoice under two programs maps independently. (7) One page, no autopaging: the walker accepts a 100-invoice horizon rather than walking has_more (recorded limitation, not a bug).
**Probe:** No direct test (grep apps/web/tests/ for getCustomerStripeInvoices | stripe-invoices = ∅). Deterministic probes executed at pin: stripeMode default (schema.ts :4); secretMap live/test/sandbox (stripe/index.ts :13-15); cus_ gate :52; invoices.list status:"paid" :68 + limit:100 :69 + expand :70 + stripeAccount :73; resource_missing :80; charges console.warn :109; commission findMany :112 + map :121 + join :173; total_excluding_tax ternary :168-169; payment_intent join :142-148; NEGATIVE probes: no autoPaging/has_more/starting_after anywhere in the kernel (single page); getCustomerStripeInvoices has exactly two callers (the route and create-manual-commissions.ts :420).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getCustomerStripeInvoices stripeAccount invoices paid refunded", limit: 10 }); // rank-1 expected: get-customer-stripe-invoices.ts
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "getCustomerStripeInvoices", direction: "inbound", depth: 1 }); // expected: stripe-invoices route + create-manual-commissions
```

## Verdict
Adopt the per-workspace mode resolution (stored integration setting → per-mode secret map) for any read against a user-connected payment account — never a global key. Adopt the `stripeAccount` header on every call so reads execute on the connected account. Adopt best-effort degradation for optional scopes (log and continue) while keeping core reads strict. Adopt derived refund truth joined from a second resource rather than trusting a stale local flag. Adapt the resource_missing→actionable-400 translation to any provider error that means "your stored pointer is stale". Omit nothing silently: skipping the mode gate lets a test connection read live data; paging past the first page (or promising more than 100 invoices) would change the contract this walker actually has.
