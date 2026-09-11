<!-- capsule-v2 -->
# Dashboard serialize with widget handlers — how do dashboards export their widgets' polymorphic state plus widget-scoped filters through a per-type handler?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** Widgets are an open-typed set (charts, tables, …) — how does export serialize their internal references without the exporter knowing every widget type?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.serializeDashboards` (113–183) + `~/db/widgets:getWidgetHandler`.

**Signature:** `serializeDashboards(context, param, req): Promise<SerializedDashboard[]>` — takes `{idMap}` and RETURNS it extended; `getWidgetHandler(context, {widget, req})` → handler exposing `serializeOrDeserializeWidget(context, widget, idMap)`.

**Data Shape:** dashboard payload: `{id: mappedComposite, title, description, order, meta, widgets: [...]}`; each widget = handler output + `filters: ExportedFilter[]` in the standard composite-id filter shape (`{id: <widgetMappedId>::<flId>, fk_column_id: mapped|null, fk_parent_id: prefixed, is_group, logical_op, comparison_op?, value?}`).

### Decisive source
```ts
for (const dashboard of await Dashboard.list(context, context.base_id)) {
  idMap.set(dashboard.id, `${dashboard.base_id}::${dashboard.id}`);   // 2-segment id
  await dashboard.getWidgets(context);
  for (const widget of dashboard.widgets) {
    const handler = await getWidgetHandler(context, { widget, req }); // polymorphic dispatch
    const serializedWidget = await handler.serializeOrDeserializeWidget(context, widget as any, idMap);
    const filters = await Filter.getFilterObject(context, { widgetId: widget.id });
    const exportedFilters = [];
    if (filters?.children?.length) {
      for (const fl of filters.children) {
        const tempFl = { id: `${idMap.get(widget.id)}::${fl.id}`,      // prefix = WIDGET id
          fk_column_id: idMap.get(fl.fk_column_id),
          fk_parent_id: `${idMap.get(widget.id)}::${fl.fk_parent_id}`,
          is_group: fl.is_group, logical_op: fl.logical_op,
          comparison_op: fl.comparison_op, comparison_sub_op: fl.comparison_sub_op, value: fl.value };
        if (tempFl.is_group) delete tempFl.comparison_op, tempFl.comparison_sub_op, tempFl.value;
        exportedFilters.push(tempFl); } }
    serializedWidgets.push({ ...serializedWidget, filters: exportedFilters });
  }
  …
}
```

**Flow:** dashboards register their composite id, then per widget resolve a type-specific handler and hand it the SAME live idMap — so whatever internal refs the widget carries get remapped inside its own serializer while the exporter owns only the generic filter envelope. Group filters shed comparison keys; leaves keep them.

**Invariant:** the exporter NEVER inspects widget internals — the handler contract (`serializeOrDeserializeWidget(ctx, widget, idMap)`) is the extension point; adding a widget type means adding a handler, not touching this loop. Filter ids are prefixed with the widget's MAPPED id, so a widget must be registered in idMap before its filters are rewritten. `serializeInterfaces`/`serializeWorkflows`/`serializeDocuments` currently return `[]` — stubs kept in the same shape so callers stay stable.

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:120-136` (idMap registration → getWidgets → handler call), `:138-164` (widget-scoped filter rewrite with group stripping), `:98-111` (the three stub serializers). Handler implementations live under `~/db/widgets` (graph: search `getWidgetHandler`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "serializeDashboards getWidgetHandler serializeOrDeserializeWidget", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the handler-dispatch pattern for open-typed embedded entities (exporter owns envelopes, handlers own bodies); adapt widget types to host; omit the stub serializers unless porting full base migration. Coverage caveat: no in-repo unit tests; source-grounded.
