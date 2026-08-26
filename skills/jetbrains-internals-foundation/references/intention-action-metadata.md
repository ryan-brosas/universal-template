<!-- capsule-v2 -->
# Intention action metadata — multi-tag EP with per-instance i18n category

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PythonCore plugin); Codebase Memory `jetbrains-pycharm`. **Question:** How does the platform register intentions when one attribute cannot carry language + class + bundle + category?

## IntentionAction compound tag
**Path/Symbol:** `plugins/python-ce/lib/*.jar:META-INF/plugin.xml` (40 `<intentionAction>` entries); platform counterpart `com.intellij.intention.intentionAction` EP (`hasAttributes="true"` style).
**Signature:** `<intentionAction><language>L</language><className>FQN</className><bundleName>messages.B</bundleName><categoryKey>INTN.category.x</categoryKey></intentionAction>`.
**Data Shape:** child elements instead of attributes — each instance carries its own bundle/category so families of intentions group under externalized categories without a shared bean.

### Decisive source
```xml
<intentionAction>
  <language>Python</language>
  <className>com.jetbrains.python.codeInsight.intentions.PyConvertMethodToPropertyIntention</className>
  <bundleName>messages.PyPsiBundle</bundleName>
  <categoryKey>INTN.category.python</categoryKey>
</intentionAction>
```

**Flow:** declare → platform instantiates className → reads family/name from its own bundle + categoryKey for settings grouping → Alt+Enter menu lists it under that category for the declared language.
**Invariant:** display strings come from THE CONTRIBUTOR'S bundle, not a central catalog — porting an intention requires porting its bundle keys. Wrong port: centralizing all intention text in one file (breaks third-party contribution symmetry).
**Probe:** deterministic: `grep -A1 '<intentionAction>' py-plugin.xml | head -4` shows the four-child shape repeated 40×.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "python convert method property intention", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt compound-tag registration where single attributes can't express per-instance metadata; adapt to your config format's nested syntax; omit IntelliJ intention lookup internals. Coverage caveat: direct jar read.
