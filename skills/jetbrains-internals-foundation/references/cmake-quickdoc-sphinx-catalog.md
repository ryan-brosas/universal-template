<!-- capsule-v2 -->
# cmake-quickdoc-sphinx-catalog — how does an IDE document a whole external DSL offline?

**Source:** JetBrains CLion installed build `2026.2.1@262.9437.136` (`plugins/cmake/docs/quickdoc/`); Codebase Memory `jetbrains-clion`. **Question:** How do you ship lookup-grade docs for thousands of DSL entities (commands, variables, properties, policies, modules) without embedding a doc server?

## Entity-classed Sphinx catalog
**Path/Symbol:** `plugins/cmake/docs/quickdoc/<entity-class>/<entity-name>.html` — 2076 content pages (2078 graph count incl. _static assets): command 143, variable 818, prop_tgt 441, module 277, policy 217, prop_sf 58, prop_gbl 43, prop_dir 38, prop_test 29, prop_cache 6, prop_inst 6.
**Data Shape:** directory = entity CLASS, filename stem = exact entity identifier (`command/set.html`, `variable/CMAKE_BUILD_TYPE.html`, `prop_tgt/OUTPUT_NAME.html`); Sphinx-generated HTML 4.01 with hashed asset refs (`_static/pygments.css?v=8e8a900e`).

### Decisive source
```
# grep -o '<title>[^<]*</title>' over three entities (executed):
command/set.html:<title>set</title>
variable/CMAKE_BUILD_TYPE.html:<title>CMAKE_BUILD_TYPE</title>
prop_tgt/OUTPUT_NAME.html:<title>OUTPUT_NAME</title>
```

**Flow:** CMake's own Sphinx docs are built once at packaging time → partitioned by entity class → UI resolves F1/hover for an entity by class+name path lookup; no index file is needed because the key IS the path.
**Invariant:** `<title>` == filename stem == lookup key (verified on 3 classes); property classes split by scope (tgt/gbl/dir/sf/test/cache/inst) mirroring CMake's own scoping — the taxonomy is the search facet; counts drift per bundled CMake version (4.3 here), so census per pin.
**Probe:** executed byte-exact pre-write: `find quickdoc -name '*.html' -not -path '*_static*' | wc -l` → `2076`; per-subdir counts as listed above; title greps as shown.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "jetbrains-clion", query: "MATCH (f:File) WHERE f.file_path STARTS WITH 'plugins/cmake/docs/quickdoc' RETURN count(f) AS quickdoc_pages", max_rows: 5 });
```
(executed live this pass → quickdoc_pages = 2078.)

## Verdict
Adopt class-partitioned static catalogs with identity-by-filename for DSL help; adapt entity classes to your domain; omit Sphinx build machinery. Companion catalog to clangtidy-check-doc-catalog — same method, different taxonomy axis.
