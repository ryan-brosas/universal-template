<!-- capsule-v2 -->
# ML completion model jars — how are per-language ranking/filter/trigger models packaged and wired?

**Source:** JetBrains IDE distributions (proprietary distribution); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How does an app ship local ML models per language as swappable plugins, and what is the descriptor→model→feature-metadata contract inside each?

## Connected graph-selected seam
**Path/Symbol:** `plugins/fullLine/lib/modules/intellij.fullLine.<lang>.local.jar` (16 languages incl. rider.cpp/rider.csharp splits) + `intellij.ml.llm.<lang>.completion.jar` twins + `intellij.searchEverywhereMl.ranking.core.jar` (7 SE models).
**Signature:** module xml: `<extensions defaultExtensionNs="org.jetbrains.completion.full.line"><fullLineLanguageSupport language="Python" implementationClass="...PythonFullLineSupporter"/><experimentConnector language="Python" .../></extensions>` + registryKey `full.line.completion.use.new.filter.python`.
**Data Shape:** each language jar carries sibling dirs: `<lang>_inline_filter_model/model.bin`, optional `_v2` twin (new model staged beside old, gated by the registry key above), `<lang>_inline_trigger_model/model.bin` + `threshold.txt` (single float, e.g. `0.872`), and `<…>_features/{all_features,float,categorical,binary}.json + features_order.txt + version.txt`. Feature JSON entries: `{"is_white_space_after_caret":{"default":0,"false":0.0,"true":1.0,"use_undefined":true}}`. SearchEverywhere: actions/files/classes/all/ec models with `_exp` experiment variants (0.14–2.1MB).

### Decisive source
```xml
<extensions defaultExtensionNs="com.intellij">
  <registryKey key="full.line.completion.use.new.filter.python"
               defaultValue="false"
               description="Use new filter model for the local LLM completions"/>
</extensions>
```
```
python_inline_trigger_model/threshold.txt        → "0.872"
python_inline_trigger_model_features/binary.json → {"is_white_space_after_caret":
                                                    {"default":0,"false":0.0,"true":1.0,
                                                     "use_undefined":true}}
```

**Flow:** core fullLine engine asks the EP for a language supporter → supporter resolves its model dirs classloader-relative → trigger gate: trigger-model score vs threshold.txt decides whether to invoke generation → filter model ranks/filters candidates → `_v2` swap flips via registryKey without repackaging.
**Invariant:** model binaries are NEVER referenced by absolute path — always `<dir>/model.bin` beside feature metadata that names the exact feature order; a porter who reorders features silently corrupts inference. Experiment (`_exp`) variants run alongside stable ones, selected externally.
**Probe:** `unzip -p plugins/fullLine/lib/modules/intellij.fullLine.python.local.jar python_inline_trigger_model/threshold.txt` → `0.872`; `unzip -l ... | grep -c model.bin` ≥ 3.
**Coverage caveat:** resource plane; .bin payloads opaque by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "completion ml ranking model", limit: 5, fields: ["signature", "name", "file"] });
// → com/intellij/codeInsight/completion/ml/* in intellij.platform.analysis.jar
```

## Verdict
Adopt: per-language model plugin shape (descriptor + EP supporter + model dir + feature schema + threshold file), v2-staged-beside-v1 with registry-gated flip, exp-variant coexistence. Adapt model formats to your runtime. Omit the weights themselves. Identical 39-jar fullLine set ships in EVERY 262 IDE (activation is product-dependent).
