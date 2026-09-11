<!-- capsule-v2 -->
# Content-based fileTypeDetector pair — how does a file get typed by sniffing its BYTES when the extension lies?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-webstorm`. **Question:** How do you register content-based (not extension-based) file-type detection, and what does the detector contract guarantee?

## The fileTypeDetector EP
**Path/Symbol:** `plugins/nodeJS/lib/nodeJS.jar:META-INF/plugin.xml:63-64` (`<extensions defaultExtensionNs="com.intellij">`).
**Signature:** `<fileTypeDetector implementation="<FQN>"/>` — optional `order="last"` attr (ordering grammar owned by extension-ordering-attributes; e.g. TextMate's detector in pycharm).
**Data Shape:** implementation FQNs may be INNER CLASSES (`NodeFileTypeDetector$JavaScriptFileTypeDetector`): one outer holder, one detector class per target type. The nodeJS plugin ships exactly two — JavaScript and TypeScript detectors — so `.js`/`.ts` files with wrong/missing extensions are re-typed by content inspection.

### Decisive source
```xml
<fileTypeDetector implementation="com.jetbrains.nodejs.util.NodeFileTypeDetector$JavaScriptFileTypeDetector" />
<fileTypeDetector implementation="com.jetbrains.nodejs.util.NodeFileTypeDetector$TypeScriptFileTypeDetector" />
```

**Flow:** user opens a file → platform tries extension mapping first (filetype-registration-contract owns that plane) → if unresolved or suspect, walks registered detectors → each detector sniffs bytes (shebang, syntax markers) and claims a type → first accepting detector wins under the ordering grammar.
**Invariant:** a content detector NEVER overrides an explicit, correctly-mapped extension type — it is the fallback for ambiguous input. Wrong port: treating detectors as the primary typing mechanism, or registering one monolithic detector instead of per-type inner classes.
**Probe:** `unzip -p plugins/nodeJS/lib/nodeJS.jar META-INF/plugin.xml | grep -c '<fileTypeDetector'` → 2 (one per inner-class detector). Cluster corroboration (reproducible census, one unzip per jar under `<product>/plugins/`, 11 installs): 52 declarations cluster-wide — webstorm 6 / pycharm 6 / rider 6 / clion 7 / goland 5 / phpstorm 6 / dataspell 2 / rubymine 6 / rustrover 6 / datagrip 2 / mps 0. Verified instances: pycharm `TextMateFileDetector order="last"` (textmate-plugin.jar), `SourceMapFileType$MyFileTypeDetector` (javascript-debugger.jar, same inner-class idiom), clion `CppHeaderFileTypeDetector` (clion-radler.jar).

## Get live surrounding code
**Retrieve:** (jar-resident manifest plane — not symbol-indexed)
```bash
unzip -p plugins/nodeJS/lib/nodeJS.jar META-INF/plugin.xml | grep '<fileTypeDetector'
```
The detector classes themselves live in compiled jar code; the manifest registration is the portable seam.

## Verdict
Adopt: content-sniffing fallback registry keyed per type, inner-class-per-detector packaging, explicit-order for late contributors. Adapt the sniffing predicates to your domain's magic numbers/shebangs. Omit IntelliJ's concrete detection heuristics (closed source). Pairs with filetype-registration-contract (extension plane) as its content-based complement.
