<!-- capsule-v2 -->
# TextMate bundle plane — how does an editor get 64 languages "for free" via a grammar-bundle convention?

**Source:** JetBrains IDE distributions (proprietary distribution; bundle JSON MIT-licensed); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How are third-party TextMate grammars integrated as loose directories with a provider EP, and what does the VSCode-compatible package.json contract contribute?

## Connected graph-selected seam
**Path/Symbol:** `pycharm/plugins/textmate-plugin/lib/bundles/<lang>/` — 64 bundles, each a LOOSE directory: `package.json` + `language-configuration.json` + `syntaxes/*.tmLanguage.json`; wiring in `textmate-plugin.jar` + `modules/intellij.textmate*.jar`.
**Signature:** EP `<extensionPoint qualifiedName="com.intellij.textmate.bundleProvider" interface="org.jetbrains.plugins.textmate.api.TextMateBundleProvider" dynamic="true"/>`; default impl scans plugin home via `PluginPathManager.getPluginHome("textmate-plugin") + lib/bundles` (string constant `lib/bundles` in TextMateServiceImplKt).
**Data Shape:** `package.json` is VSCode-shaped: `contributes.languages[{id, aliases, extensions[], configuration}]` + `contributes.grammars[{language, scopeName:"source.clojure", path}]` + `configurationDefaults`. `language-configuration.json`: comments/brackets/autoClosingPairs (with `notIn:["string"]`)/surroundingPairs/folding (`offSide:true`).

### Decisive source
```json
{"contributes":{"languages":[{"id":"clojure","aliases":["Clojure"],
   "extensions":[".clj",".cljs",".cljc",".cljx",".clojure",".edn"],
   "configuration":"./language-configuration.json"}],
 "grammars":[{"language":"clojure","scopeName":"source.clojure",
   "path":"./syntaxes/clojure.tmLanguage.json"}],
 "configurationDefaults":{"[clojure]":{"diffEditor.ignoreTrimWhitespace":false}}}}
```

**Flow:** bundleProvider EP resolves providers → default provider lists `lib/bundles/*` dirs → each dir's package.json contributes file-type extensions + grammar → onboarding a NEW language = dropping one directory; zero descriptor edits.
**Invariant:** bundles stay OUTSIDE jars as loose files (unlike every other resource plane) so users can add/edit them at runtime; registryKey `textmate.line.highlighting.limit=20000` bounds pathological lines. The fileType itself is registered with the standard `fieldName="INSTANCE"` singleton pattern.
**Probe:** `ls plugins/textmate-plugin/lib/bundles | wc -l` → `64`; `cat plugins/textmate-plugin/lib/bundles/clojure/package.json | python3 -m json.tool | head -5`.
**Coverage caveat:** resource plane; the loader logic was confirmed by class-string inspection (`lib/bundles`, `PluginPathManager`) since bytecode isn't decompiled in this corpus.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "textmate bundle syntax highlighting", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: directory-per-language bundle convention + VSCode package.json compatibility + provider EP for alternate sources. Adapt grammar engine to your host. Omit the grammars (third-party MIT data). This is the escape hatch that keeps first-party language plugins from having to cover long-tail formats.
