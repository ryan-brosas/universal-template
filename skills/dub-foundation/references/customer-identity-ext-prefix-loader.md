<!-- capsule-v2 -->
# Customer identity ext_ prefix loader — how does one path parameter address two identity keys (row id vs external id) without ambiguity?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** How should a detail-route loader dispatch between internal ids and user-supplied external ids, and what must the not-found message teach?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/api/customers/get-customer-or-throw.ts:getCustomerOrThrow` (:5-54).
**Signature:** `getCustomerOrThrow({ id, workspaceId }, { includeExpandedFields? = false }) => Promise<CustomerWithLink>`.
**Data Shape:** `id` is EITHER `cus_<nanoid>` (primary key) OR `ext_<externalId>` (caller's namespaced key). Dispatch is a string PREFIX, not a query param.

### Decisive source
```ts
const customer = await prisma.customer.findUnique({
  where: {
    ...(id.startsWith("ext_")
      ? { projectId_externalId: { projectId: workspaceId, externalId: id.replace("ext_", "") } } // :21-27 COMPOUND unique ⇒ tenant-scoped BY CONSTRUCTION
      : { id }),
  },
  ...(includeExpandedFields && { include: { link: true, programEnrollment: { include: { partner: true, discount: true } } } }),
});
if (!customer || customer.projectId !== workspaceId) {
  throw new DubApiError({ code: "not_found",
    message: "Customer not found. Make sure you're using the correct customer ID (e.g. `cus_…`) or external ID (has to be prefixed with `ext_`).", }); // :45-51 TEACHING message
}
```

**Flow:** prefix sniff → ext_ ⇒ compound-unique lookup pre-bound to the caller's workspace; otherwise bare primary-key lookup → row missing OR wrong tenant collapses to ONE not_found whose message teaches the `ext_` convention.
**Invariant:** External-id resolution can never cross tenants because the compound unique includes projectId — tenancy is structural, not an added where-clause. Uniform not-found for "missing" and "not yours" kills the existence oracle. Note the per-plane divergence: the LIST path's cursor validation (get-customers.ts :43-48) also uses one uniform message but code `unprocessable_entity`, while this loader uses `not_found` — uniformity is preserved WITHIN each plane, not platform-wide. Contrast links' loader alias ladder (cursor-identity-validation capsule): customers use prefix-dispatch instead of domain→_root collapse.
**Probe:** No direct test for this loader (tests/**/*customer* = ∅). Deterministic probes: startsWith("ext_") :21, compound key :23-26, tenant re-check :45, teaching message :48-49.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getCustomerOrThrow customer ext_ externalId prefix", limit: 5 }); // rank-1 :5-54
```

## Verdict
Adopt prefix-dispatched dual-key addressing with a compound-unique tenant-scoped external key and a teaching error message. Adapt the prefix token (`ext_`) to your API's existing conventions — but never accept bare external ids, or collisions across tenants become possible. Omit the expanded-fields switch if your serializer handles joins elsewhere.
