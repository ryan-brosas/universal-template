<!-- capsule-v2 -->
# Permission bit-string algebra — how do you encode CRUDS permission sets as DB strings and combine rule outcomes without a record, ending in exactly allow/deny/mixed?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the algebra that turns per-rule permission bits into a final table/column permission verdict (the substrate the GranularAccess rule engine consumes)?

## `[+bits][-bits]` text codec + associative partial-combination with finalized-once semantics
**Path/Symbol:** `app/common/ACLPermissions.ts:parsePermissions` (:83–102), `permissionSetToText` (:108–122), `combinePartialPermission` (:138–146), `mergePermissions` (:171–178), `toMixed` (:185–187), `summarizePermissionSet` (:193–207), `splitSchemaEditPermissionSet` (:227–235).
**Signature:** `parsePermissions(text: string): PartialPermissionSet` / `combinePartialPermission(a: PartialPermissionValue, b: PartialPermissionValue): PartialPermissionValue` / `mergePermissions<T,U>(psets: PermissionSet<T>[], combine: (bits: T[]) => U): PermissionSet<U>` / `toMixed(pset: PartialPermissionSet): MixedPermissionSet`.
**Data Shape:** `PermissionValue = "allow" | "deny"`; `MixedPermissionValue = PermissionValue | "mixed"`; `TablePermissionValue = MixedPermissionValue | "mixedColumns"`; `PartialPermissionValue = PermissionValue | "allowSome" | "denySome" | "mixed" | ""`; `PermissionSet { read, create, update, delete, schemaEdit }`. DB text form: `"[+CRUDS bits][-bits]"`, aliases `all`/`none`, empty string valid.

### Decisive source
```ts
export function combinePartialPermission(a: PartialPermissionValue, b: PartialPermissionValue): PartialPermissionValue {
  if (!a) { return b; }
  if (!b) { return a; }
  // If the first is uncertain, the second may keep it unchanged, or make certain, or finalize as mixed.
  if (a === "allowSome") { return (b === "allowSome" || b === "allow") ? b : "mixed"; }
  if (a === "denySome")  { return (b === "denySome" || b === "deny") ? b : "mixed"; }
  // If the first is certain, it's not affected by the second.
  return a;
}

export function toMixed(pset: PartialPermissionSet): MixedPermissionSet {
  return mergePermissions([pset], ([bit]) => (bit === "allow" || bit === "mixed" ? bit : "deny"));
}
```

**Flow:** ACL rule strings parse into per-bit sets (`+R-D` → read allow, delete deny; `all`/`none` expand via alias table) → rules evaluated WITHOUT a record first combine their PartialPermissionSets left-to-right where earlier wins: empty passes through, an uncertain side (`*Some`) can be resolved by a certain later value or finalize to `mixed`, but any CERTAIN earlier value is immutable → row-dependent rules rewrite allow/deny to allowSome/denySome (`makePartialPermissions`) before combining → leftover uncertain bits fall through `toMixed` to deny (fail-closed; "should never be needed because the hard-coded fallback rules should finalize all bits") → table-level evaluation distinguishes `mixedColumns` when column rules but not row rules vary, enabling skip-record optimizations.
**Invariant:** The combine operation is ASSOCIATIVE ((a+b)+c == a+(b+c), stated in-source) — order-dependent precedence lives in the CALLER's ordering of rule sets, not in the operator. `""` is a real value meaning "no opinion", distinct from deny. Text round-trip drops everything except allow/deny ("anything else will NOT be included"), so persistence must happen only after resolution. `summarizePermissionSet` ignores the Some-suffixes: a set mixing allow-flavored and deny-flavored bits summarizes to mixed. Schema-edit splits out because schema permissions ride a different authorization path than data.
**Probe:** No direct unit test file for ACLPermissions.ts (coverage caveat — it is exercised transitively by the rule-engine suite around PermissionInfo/GranularAccess). Deterministic source probes: `grep -c "associative property" app/common/ACLPermissions.ts` = 1 (:136); `grep -n '"mixedColumns"' app/common/ACLPermissions.ts` hits :21 only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "combinePartialPermission mergePermissions toMixed ACLPermissions", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the value-level algebra under ANY record/no-record two-phase permission engine: five fixed verbs, one associative combiner, fail-closed normalization. Adapt bit names and the mixedColumns-style optimization to your resource model. Omit the text codec if your rules persist structurally — but keep the empty-means-no-opinion distinction either way.
