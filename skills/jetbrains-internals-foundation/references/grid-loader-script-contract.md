<!-- capsule-v2 -->
# Scripted grid data loaders — how do you add a tabular import/export format WITHOUT compiled feature code?

**Source:** DataGrip installed distribution `dist@262.9437.163` (proprietary; study/reference only); Codebase Memory `jetbrains-datagrip`. **Question:** What is the complete contract a Groovy data-loader script must satisfy for the database grid to discover, register, and run it?

## Graph-selected seam: loader scripts as loose plugin resources
**Path/Symbol:** `plugins/grid-loader-json/external-extensions/com.intellij.database/data/loaders/JSON.groovy:1-11` and `plugins/grid-loader-xls/.../XLS.groovy:1-11` (`LOADER.load`, graph qn `...data.loaders.JSON.loadJson` 13-29).
**Signature:** `LOADER.load { ctx -> ... }`; inside: `loadJson(ctx.getParameters()["FILE"], ctx.getDataConsumer())`.
**Data Shape:** host-injected global `LOADER`; `ctx.getParameters()["FILE"]` = filesystem path string; `ctx.getDataConsumer()` = row consumer with three call shapes: `consume(name, value)` (object-as-column-stream), `consumeColumns(String[] names, Class[] types)` then `consume(Object[] row)` (array-of-maps), `consume(Object[] row)` (positional rows).

### Decisive source
```groovy
// JSON.groovy line 1 — registration metadata lives in a COMMENT:
// IJ: extensions = json displayName = JSON tableFirstFormat=false
package extensions.data.loaders

@Grab("com.fasterxml.jackson.core:jackson-core:2.16.1")
@Grab("com.fasterxml.jackson.core:jackson-databind:2.16.1")

LOADER.load { ctx ->
  loadJson(ctx.getParameters()["FILE"], ctx.getDataConsumer())
}
```
```groovy
// XLS.groovy line 1 — multi-extension + no format flag:
// IJ: extensions = xls;xlsx displayName = XLS
```

**Flow:** plugin ships script under `external-extensions/<host-plugin-id>/data/loaders/<Name>.groovy` → runtime engine parses line-1 `// IJ:` header (`extensions=` semicolon list binds file extensions; `displayName=` UI label; `tableFirstFormat=` flips import table/column precedence) → compiles script body → invokes the single `LOADER.load { ctx -> }` entry point with FILE parameter + data consumer → consumer calls build the grid model.
**Invariant:** exactly ONE top-level `LOADER.load { ctx -> }` block per script; extension list is the ONLY filename routing (no magic detection); the directory path must mirror the HOST plugin id (`com.intellij.database`), not the loader plugin's own id.
**Probe:** `head -1 plugins/grid-loader-{json,xls}/external-extensions/com.intellij.database/data/loaders/*.groovy` → the two `// IJ:` lines above; `grep -n 'LOADER.load' ...` → both at line 9. (Executed 2026-08-25.)
**Coverage caveat:** JSON.groovy is parse_partial (whole file 1-160 flagged by tree-sitter); every cited range was read directly from disk before citing.
Latent-defect note (honest observation): `processValueAsRows` (JSON.groovy:111-114) references undeclared `name` — the scalar-top-level JSON path throws MissingPropertyException as shipped. Port the dispatch, fix the scalar arm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-datagrip", query: "data loader import export", limit: 10 });
```
(Live result 2026-08-25: loadJson 13-29, addValue 157-160, loadXls 13-20, produceSheet 22-36, extractRow 38-50.)

## Verdict
Adopt: comment-carried registration metadata (zero-compile registration), one-closure entry point, ctx parameter/consumer split, extension-list routing. Adapt the header grammar keys to your host's parser; keep `tableFirstFormat` semantics if you have an import-direction choice. Omit Groovy/Grape specifics if your host scripts run on another engine — pair with plugin-external-resources-unpack-plane for discovery and offline-grape-dependency-vendoring for deps.