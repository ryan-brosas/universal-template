<!-- capsule-v2 -->
# NatVis declarative formatter model — how do you parse MSVC-style .natvis visualization rules into a typed model a debugger can match and render?

**Source:** JetBrains Rider installed build `RD-262.8665.400` (`plugins/cidr-debugger-plugin/bin/helpers/jb_declarative_formatters/`, 13 modules / 2,243L); Codebase Memory `jetbrains-rider`. **Question:** What data model and matching order let one formatter engine serve natvis-style type visualizations (summaries, expanders, string views, smart pointers) across debuggers?

## TypeVizStorage as the decisive instance
**Path/Symbol:** `type_viz_storage.py:TypeVizStorage` (:48-182), `Item.ensure_descriptors_sorted` (:55-67), `DirectAcyclicGraph.sort` (:15-34); entry chain `renderers/jb_lldb_natvis_loader.py:natvis_loader` (22L): parse file → `storage.add_type` ×N → `storage.generate_top_level_methods(RENDER_LOG, JetvisProxy.is_enabled())`.
**Signature:** `natvis_parse_file(filepath, log, jetvis_enabled) -> Iterable[TypeViz]`; `storage.add_type(type_viz)`.
**Data Shape:** per storage Item: `exact_match[]` vs `wildcard_match[]` descriptor lists (key built from `TypeNameTemplate`), each descriptor holding visualizers sorted by `-priority` plus `more_specific_descriptors` DAG edges; item-provider taxonomy = Single / Expanded / ArrayItems / IndexListItems / LinkedListItems / TreeItems / CustomListItems (+ Synthetic).

### Decisive source
```python
def ensure_descriptors_sorted(self):
    if self.descriptors_was_sorted:
        return
    for descriptor in self.exact_match:
        descriptor.visualizers.sort(key=lambda x: -x.priority)
    ...
    graph = DirectAcyclicGraph(self.wildcard_match, lambda m: m.more_specific_descriptors)
    self.wildcard_match = list(graph.sort())
    self.descriptors_was_sorted = True
```
(`from lldb.formatters.Logger import Logger` in type_viz.py:11 proves execution INSIDE LLDB's Python.)

**Flow:** natvis XML parsed (parsers/natvis/natvis_parser.py; C++ type expressions pre-parsed by parsers/cpp_parser.py) → each viz registered under every declared name template into exact or wildcard buckets (dirty flag reset) → on FIRST match request the bucket sorts lazily: priority desc within descriptors, topological most-specific-first over the wildcard DAG → renderer walks summaries/item providers/string views; synthetic items always hide raw view (`TypeVizSyntheticItem.hide_raw_view = True`).
**Invariant:** matching order is (exact before wildcard) then specificity (DAG) then priority — preserve all three layers or user-declared specializations lose to generic ones; sorting is lazy with a dirty flag so registration stays cheap and re-registration invalidates exactly once. Wrong port: sorting at insert time (breaks incremental adds) or flattening the DAG (loses specificity semantics). Inline comment records an LLDB limitation: smart-pointer Usage 'Full' cannot be expressed (no conversion-operator support), folded into 'Indexed' — neither stl.natvis nor Unreal.natvis uses 'Full'.
**Probe:** structural probes GREEN: package total 2243L (`wc -l *.py | tail -1`); provider taxonomy classes ≥ 8 in type_viz_item_providers.py; loader chain verified by direct read of the 22L loader (parse→register→generate pipeline). No bundled .natvis ships in this plugin — files arrive at runtime (loader takes a filepath), so fixture-level evidence is intentionally absent; model facts are code-level.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", name_pattern: ".*TypeVizStorage.*", limit: 6 });
// -> ...type_viz_storage.TypeVizStorage Class 48-182
```

## Verdict
Adopt the three-layer match order and lazy dirty-flag sorting for any declarative visualization engine; adopt the provider taxonomy as the NatVis section mapping. Adapt parser specifics to your grammar. Omit LLDB API glue (renderers/) unless targeting LLDB. Next-pass queue owns the intrinsic grammar (type_viz_intrinsic.py) and generated-method injection (type_viz_top_level_methods + lazy declarations).
