<!-- capsule-v2 -->
# Experimental feature gating + live template macro/context — percentOfUsers vocabulary and baseContextId chains

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` / `WebStorm WS-262.9437.145`; Codebase Memory `jetbrains-pycharm`. **Question:** How are features flagged experimental (and rolled out by percentage), and how do live-template macros and contexts compose their applicability?

## A. experimentalFeature
**Path/Symbol:** `intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` — `<extensionPoint name="experimentalFeature" beanClass="com.intellij.openapi.application.ExperimentalFeatureImpl" dynamic="true"/>`.
**Signature:** `<experimentalFeature id="<feature-key>" percentOfUsers="<int>">` with `<description>` child text.
**Data Shape:** py 12 rows, ws 12 rows; the ENTIRE shipped percentOfUsers vocabulary is `{100, 0}` (py: 10×"100", 2×"0"; ws identical) — 100 = announced/exposed, 0 = dark-launched/invisible; intermediate percentages exist in the schema but are unused in shipped builds.

### Decisive source
```xml
<!-- intellij.platform.ide.impl.jar:META-INF/LangExtensions.xml:292-297 -->
<experimentalFeature id="editor.reader.mode" percentOfUsers="100">
  <description>The Reader Mode is intended for comfortable code browsing rather than modification. ...
  </description>
</experimentalFeature>
```

**Flow:** registry reads declared features → user's bucket vs percentOfUsers decides availability → description surfaces in feature announcements.
**Invariant:** a feature id here gates CODE elsewhere via the same string key; wrong port = declaring the feature but keying code by a different id (gate silently inert).

## B. liveTemplateMacro + liveTemplateContext
**Path/Symbol:** `intellij.platform.analysis.jar:META-INF/Analysis.xml` — `<extensionPoint name="liveTemplateMacro" interface="com.intellij.codeInsight.template.Macro" dynamic="true"/>` and `<extensionPoint name="liveTemplateContext" beanClass="com.intellij.codeInsight.template.LiveTemplateContextBean" dynamic="true"><with attribute="implementation" implements="com.intellij.codeInsight.template.TemplateContextType"/></extensionPoint>`.
**Signature:** `<liveTemplateMacro implementation="<Macro FQN>"/>` (py 66) | `<liveTemplateContext id contextId implementation [baseContextId] [order]/>` (py 14).
**Data Shape:** macros = `$var$` expression functions (no attributes beyond class); contexts = typed tree nodes — `contextId` is the logical key, `baseContextId` (24/42 cluster rows) PARENTS it into an applicability lattice (`baseContextId="HTML"` under HTML, `"XML"` under XML...), `order="last"` positions within siblings.

### Decisive source
```xml
<!-- intellij.platform.ide.impl.jar:META-INF/LangExtensions.xml:974 -->
<liveTemplateContext id="OTHER" contextId="OTHER"
                     implementation="com.intellij.codeInsight.template.EverywhereContextType"
                     order="last"/>
```

**Flow:** template expansion → macro calls evaluated against current editor state → context tree walked from leaf up through baseContextId chain to decide whether the template is offered at the caret.
**Invariant:** a context is enabled only if its WHOLE baseContextId ancestor chain is enabled — porting a context without its parents orphans it.
**Probe:** from install root: `for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -o 'percentOfUsers="[0-9]*"' | wc -l` summed → 12 (py) / 12 (ws); vocabulary: pipe to `sort | uniq -c` → only "100" and "0". `<liveTemplateMacro ` sum → 66 (py); `<liveTemplateContext ` sum → 14 (py).

## Get live surrounding code
**Retrieve:** manifest-only plane — no BM25 symbol surface for these EP tokens. Deterministic primitive:
```bash
unzip -p lib/intellij.platform.ide.impl.jar META-INF/LangExtensions.xml | grep -n 'id="OTHER"'
```
→ line 974 at pin PY-262.9437.214.

## Verdict
Adopt two-tier flagging (announced vs dark launch) keyed by exact string ids and parent-chained template contexts; adapt rollout bucketing to your host; omit IntelliJ's announcement UI plumbing. Boundary: registry-key runtime flags live in registry-key-runtime-tuning; this capsule owns DECLARED FEATURE FLAGS + TEMPLATE COMPOSITION metadata.
