<!-- capsule-v2 -->
# Language seam registration — one language × N editor extension points

**Source:** JetBrains IDE installed builds `PyCharm 262.9437.214` / `Rider 262.8665.400`; Codebase Memory `jetbrains-pycharm`, `jetbrains-rider`. **Question:** What is the minimal complete set of registrations to light up a language, and how do seams stay orthogonal?

## language-keyed seams
**Path/Symbol:** PyCharm `plugins/python-ce/lib/*.jar:META-INF/plugin.xml` (syntax.core/syntax modules) + Rider Unity backend module (ShaderLab block).
**Signature:** every seam EP carries `language="<name>"`: `<lang.parserDefinition|lang.formatter|lang.commenter|annotator|completion.contributor|psi.referenceContributor|quoteHandler|lang.syntaxHighlighterFactory|spellchecker.support ...>`.
**Data Shape:** the platform declares these EPs with beanClass=`com.intellij.lang.LanguageExtensionPoint` + `<with attribute="implementationClass" implements="<seam interface>"/>` (see META-INF/CodeStyle.xml for lang.formatter); contributions dispatch by language key at runtime.

### Decisive source
```xml
<lang.formatter language="Python" implementationClass="...PythonFormattingModelBuilder" />
<preFormatProcessor implementation="...PyPreFormatProcessor" />   <!-- language-agnostic seam -->
<postFormatProcessor implementation="...PyTrailingCommasPostFormatProcessor" />
<lang.commenter language="Python" implementationClass="com.jetbrains.python.PythonCommenter" />

<!-- Rider: a full language lit up in one plugin block -->
<fileType name="ShaderLab" ... extensions="shader" />
<lang.parserDefinition language="ShaderLab" implementationClass="...ShaderLabParserDefinition" />
<lang.syntaxHighlighterFactory language="ShaderLab" implementationClass="..." />
<completion.contributor language="ShaderLab" implementationClass="...ProtocolCompletionContributor" />
```

**Flow:** register fileType (+language) → add per-seam EPs keyed to that language → IDE routes editor events (parsing, formatting, completion, highlighting) through all contributors registered for the key.
**Invariant:** some seams are language-keyed (`lang.*`, `annotator`, `completion.contributor`) while others are GLOBAL hooks ordered across languages (`pre/postFormatProcessor`, `enterHandlerDelegate` with `order="first"`) — confusing the two breaks cross-language behavior. Wrong port: assuming formatter/completion need one monolithic registration; they compose per seam.
**Probe:** deterministic: `grep -oE 'language="[A-Za-z]+"' py-plugin.xml | sort | uniq -c | head` shows per-language seam multiplicity.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "inspection profile highlight level", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt seam-per-extension-point design keyed by capability id; adapt which seams exist in your host; omit IntelliJ PSI specifics. Coverage caveat: direct jar read.
