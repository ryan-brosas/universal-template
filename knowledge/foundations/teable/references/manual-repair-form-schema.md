<!-- capsule-v2 -->
# Manual-repair form schema — how does a rule declare a type-safe, localizable confirmation form without leaving the zod world?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do you turn a zod object into a UI-renderable repair form (widgets, options, defaults) and back into validated values?

## ManualRepairSchema WeakMap metadata + serializer
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/core/ManualRepairSchema.ts` — registries (:24–26), `unwrapSchema` (:31–59), `serializeManualRepairSchema` (:141–171); consumers: `JunctionTableRule.ts` missingHostSchema schema (:135–174), orphan-rows schema (:788–838), `UniqueIndexRule.ts` duplicate-clearing schema (:42–80).
**Signature:** `withManualRepairFormMeta(z.object({...}), {title?,description?,submitLabel?})` / `withManualRepairFieldMeta(z.enum([...])|z.string()|z.boolean(), {widget?,title?,options?,description?})` → `serializeManualRepairSchema(schema): Result<SchemaRuleManualRepairSchema, Error>`.
**Data Shape:** serialized form = `{type:'object', title?, description?, submitLabel?, required?, properties: Record<string,{type:'string'|'boolean', widget:'select'|'text'|'textarea'|'checkbox', options?: [{value,label{key,fallback,values}}], defaultValue?}>}`.

### Decisive source
```ts
const formMetaRegistry = new WeakMap<ZodTypeAny, ManualRepairFormMeta>();
const fieldMetaRegistry = new WeakMap<ZodTypeAny, ManualRepairFieldMeta>();

// unwrap ladder: Optional/Nullable mark not-required; ZodDefault yields defaultValue
for (;;) {
  if (current instanceof z.ZodOptional || current instanceof z.ZodNullable) {
    required = false; current = current.unwrap(); continue;
  }
  if (current instanceof z.ZodDefault) {
    const raw = current._def.defaultValue;
    if (typeof candidate === 'string' || typeof candidate === 'boolean') defaultValue = candidate;
    current = current._def.innerType; continue;
  }
  return { schema: current, required, defaultValue };
}
```

**Flow:** rule defines its form once as a private zod object with enum resolutions (`z.enum(['create_missing_host_schema']).default('create_missing_host_schema')`) → when validation fails with a coded reason, `getRepairHint` serializes the form into the hint → UI renders select/checkbox widgets → user values flow back as `SchemaRuleManualRepairValues` → `rule.manualRepair` re-validates the resolution string and errors 'Unsupported manual repair strategy' on anything but the declared enum.
**Invariant:** only ZodEnum/ZodString/ZodBoolean serialize — anything else is an explicit error, so forms can't silently lose fields; metadata lives in side WeakMaps keyed by schema identity so zod types stay plain.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/core/RuleRepairMetadata.spec.ts` (describe serializeManualRepairSchema :28); pglite behavior pin :2055 'should require manual repair when the junction table host schema is missing' asserts `manualRepairSchema?.properties.resolution` exists.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "withManualRepairFormMeta withManualRepairFieldMeta serializeManualRepairSchema", limit: 10 });
```

## Verdict
Adopt WeakMap-attached form metadata + strict three-type serialization + enum-as-resolution-contract; adapt widget names/i18n envelope to host UI kit; omit teable's i18n key naming scheme.
