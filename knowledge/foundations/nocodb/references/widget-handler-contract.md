<!-- capsule-v2 -->
|# Widget handler contract — polymorphic per-type serialization behind a CE no-op base

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** The dashboards exporter calls `getWidgetHandler` — what does the seam guarantee, and what is the CE/EE split hiding here?

## Path/Symbol
`packages/nocodb/src/db/widgets/index.ts:getWidgetHandler` (3–5, whole file); `packages/nocodb/src/db/widgets/base-widget.handler.ts:BaseWidgetHandler` (14–37); consumer `modules/jobs/jobs/export-import/export.service.ts:127` (inside serializeDashboards).

**Signature:** `getWidgetHandler(..._params): Promise<BaseWidgetHandler>`; methods: `validateWidgetData(...): []`, `getWidgetData(_): {}`, `formatValue(...): {}`, `serializeOrDeserializeWidget(...): {}`, `extractDependencies(_widget): WidgetDependencies`.

**Data Shape:** `WidgetDependencies = {columns: WidgetDependency[], models: [], views: []}`, each `{id, path?, widgetType?, widgetSubtype?}` — the declared column/model/view surface a widget needs, independent of its payload.

### Decisive source
```ts
// index.ts — the ENTIRE CE factory:
export async function getWidgetHandler(..._params: any) {
  return new BaseWidgetHandler();
}
// base-widget.handler.ts — every method a type-specific handler must fill:
async serializeOrDeserializeWidget(..._params: Array<unknown>) { return {}; }
public extractDependencies(_widget: any): WidgetDependencies {
  return { columns: [], models: [], views: [] };
}
```

**Flow:** exporter iterates dashboard widgets → awaits the factory → delegates serialize/deserialize passing the LIVE idMap so widget internals remap like everything else (export-dashboard-widgets.md) → dependencies feed cross-base column filtering. In CE every widget gets the same handler whose methods are shape-correct no-ops.

**Invariant:** (1) Factory indirection is THE porting point: callers never construct handlers directly, or EE-style per-widgetType dispatch becomes impossible to add without touching call sites. (2) No-op must be SHAPE-correct (`{}`/empty arrays), never null — consumers destructure unconditionally. (3) `_params` convention marks deliberate parameter-ignorance in CE; an EE override narrows signatures but stays assignable. (4) Third instance of the edition-skew pattern (migration-ee-ce-skew, jobs-module-wiring): CE ships a structural stub, EE swaps implementation.

**Probe:** no unit test upstream. Source-grounded probe: index.ts whole file (5 L), base-widget.handler.ts:15-36 (all five bodies), export.service.ts:127-135 (call site carrying idMap).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getWidgetHandler BaseWidgetHandler extractDependencies WidgetDependencies", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt factory-indirection + shape-correct-no-op + WidgetDependencies declaration form; adapt method names; omit EE handlers (not in this tree). Coverage caveat: no in-repo unit tests; source-grounded.
