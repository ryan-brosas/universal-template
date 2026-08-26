<!-- capsule-v2 -->
# go-openapi-src published-source plane — which Go API classes does JetBrains publish source for, and what does a minimal published plane look like?

**Source:** JetBrains GoLand installed distribution (proprietary; these 5 files carry Apache-2.0 headers — study/reference use only, cite never vendor) `GO-262.9437.195`; Codebase Memory `jetbrains-goland`. **Question:** a porter exposing an extensibility contract wants to know what "publishing source" means in an otherwise compiled install — which files qualify and with what guarantees?

## Published-source artifact inside a compiled plugin
**Path/Symbol:** `plugins/go-plugin/lib/src/go-openapi-src.jar` — exactly 5 files: `com/goide/GoOsManager.java`, `com/goide/codeInsight/imports/GoImportsWeigher.java`, `com/goide/completion/GoImportPathsProvider.java`, `com/goide/documentation/GoAdditionalDocumentationProvider.java`, `com/goide/project/GoRootsProvider.java`.
**Signature:** `public interface GoRootsProvider { ExtensionPointName<GoRootsProvider> EP_NAME = ExtensionPointName.create("com.goide.rootsProvider"); Collection<VirtualFile> getGoPathRoots(Project, Module); ... }.
**Data Shape:** interface contracts + tiny managers only; every file either declares an `ExtensionPointName` or implements a provider SPI; Apache-2.0 header on each; zip timestamps stripped (1980-00-00).

### Decisive source
```java
// com/goide/project/GoRootsProvider.java (Apache-2.0 header elided)
public interface GoRootsProvider {
  ExtensionPointName<GoRootsProvider> EP_NAME = ExtensionPointName.create("com.goide.rootsProvider");
  /** @return whether IDE should build index for entire GOPATH.
   *  First non-unsure response will be considered as a result. */
  default @NotNull ThreeState indexGoPathSources(@NotNull Project project) { return ThreeState.UNSURE; }
  /** @return the default GOPATH value... since go1.8, the default GOPATH is ~/go */
  default @Nullable VirtualFile getDefaultGoPath(@Nullable Project project, @Nullable Module module) { return null; }
}
```

**Flow:** implementor contributes `com.goide.rootsProvider` → host asks roots (GOPATH/src/bin) for env+indexing → tri-state `indexGoPathSources` folds across providers until first UNSURE-free answer → default methods keep older implementors source-compatible.
**Invariant:** the published set is PER-PRODUCT CURATED, not uniform: Go ships **5** files where PyCharm ships 271 (`openapi-src-artifact-class`). Publishing source = publishing the EXTENSION CONTRACTS third parties implement, never implementation internals. Tri-state "first decided wins" matches the py-inspection force-enable grammar — reuse the vocabulary, don't invent booleans.
**Probe:** `unzip -l plugins/go-plugin/lib/src/go-openapi-src.jar | grep -c '\.java'` → `5`; `unzip -p …jar com/goide/project/GoRootsProvider.java | head -2` → Apache license line.

## Get live surrounding code
**Retrieve:** (expectation: zero symbol nodes — jar resources are graph-dark in this project; unrelated TS hits are noise)
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-goland", query: "GoRootsProvider roots provider", limit: 5, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-goland", paths: ["plugins/go-plugin/lib/src/go-openapi-src.jar"] }); // no_recorded_issue
```

## Verdict
Adopt: publish exactly your third-party implementor surface as readable source with stable licenses; per-product curation over uniformity; tri-state fold for optional policy answers. Adapt: file set to your own EP inventory. Omit: treating the rest of the install as readable source — it is compiled and proprietary.
