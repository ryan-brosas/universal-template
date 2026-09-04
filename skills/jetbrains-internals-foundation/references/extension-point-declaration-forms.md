<!-- capsule-v2 -->
# Extension point declaration forms — interface or beanClass?

**Source:** JetBrains IDE installed build (Apache-2.0 headers) `PyCharm 262.9437.214`; Codebase Memory `jetbrains-pycharm`. **Question:** When declaring an extension point, when must you use `interface=` vs a `beanClass` with `<with>`, and what does `dynamic` control?

## Extension-point catalog
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` (327 EPs; same file across IDEs — see cluster-platform-parity-note).
**Signature:** `<extensionPoint name="..." [qualifiedName="ns.name"] [interface="FQN" | beanClass="FQN"] dynamic="true|false" [area="IDEA_PROJECT"]/>`.
**Data Shape:** name → consumed as `<name>` under `defaultExtensionNs` of the declaring plugin id; `interface` form = extension attribute IS the interface implementation; `beanClass` form = XML attributes parsed into that bean class; optional `<with attribute="X" implements="I"/>` children pin which bean attributes must implement which interfaces.

### Decisive source
```xml
<extensionPoint name="appStarter" beanClass="com.intellij.openapi.application.ApplicationStarterEP" dynamic="true">
  <with attribute="implementation" implements="com.intellij.openapi.application.ApplicationStarter"/>
</extensionPoint>
...
<extensionPoint name="selectInTarget"
                interface="com.intellij.ide.SelectInTarget"
                area="IDEA_PROJECT"
                dynamic="true"/>
```

**Flow:** declare EP in an `<extensionPoints>` block → other plugins contribute `<extensions defaultExtensionNs="<owner>"><epName .../></extensions>` → container validates contributions against interface or `<with>` contracts at parse time.
**Invariant:** exactly one of `interface` / `beanClass` per EP; every `<with>` attribute on a beanClass EP must exist on the bean and implement the named interface. Wrong port: adding `<with>` to an interface-form EP, or contributing attributes the bean cannot parse.
**Probe:** no test runner for installed builds — deterministic probe: `unzip -p <ide>/lib/intellij.platform.ide.impl.jar META-INF/PlatformExtensionPoints.xml | grep -A2 'name="appStarter"'` shows beanClass + with pair.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "pydevd debugger tracing", limit: 10, fields: ["signature", "name", "file"] });
```
(XML resources are not symbol-indexed; retrieval demonstrates the code plane the platform jar ships with — e.g. helpers/pydev/pydevd.py:3457.)

## Verdict
Adopt the two-form grammar and `<with>` contract checking for any capability registry; adapt bean classes to your host's config parser; omit IntelliJ container semantics you don't port. Coverage caveat: manifest evidence is direct jar extraction (XML not indexed), not graph-verified.
