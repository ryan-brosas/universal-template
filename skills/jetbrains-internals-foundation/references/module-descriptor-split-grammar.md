<!-- capsule-v2 -->
# Module-descriptor split grammar (`<idea-plugin>` + `<content>` XInclude) — how does one module jar carry BOTH a dependency manifest and an extension body?

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`lib/intellij.platform.debugger.impl.jar:intellij.platform.debugger.impl.xml` [49 lines] + `intellij.platform.debugger.impl.content.xml` [218 lines]); Codebase Memory `jetbrains-pycharm`. **Question:** When a generated module descriptor must stay pure for tooling, where do hand-written extensions go and how do the halves rejoin?

## The two-file split
**Path/Symbol:** `intellij.platform.debugger.impl.xml:1-4` header comment states the contract verbatim ("This file contains only v2 dependencies. All new extensions, actions, services, extension points, etc. should go to intellij.platform.debugger.impl.content.xml"); :5 root `<idea-plugin visibility="public" xmlns:xi=...>`; :7-45 `<dependencies><module name="..."/>×37`; :48 `<xi:include href="intellij.platform.debugger.impl.content.xml"/>`.
**Signature:** `<xi:include href="<module>.content.xml"/>` as the LAST child of the generated descriptor; content file root is a bare `<idea-plugin>` (no visibility attr) holding `<extensionPoints>`/`<extensions>`/`<actions>`/`<projectListeners>`.
**Data Shape:** generated half = ONLY `<dependencies>` module tokens (+ region markers `<!-- region Generated dependencies - run 'Generate Product Layouts' to regenerate -->`); hand half = everything else. The same split recurs per jar: debugger.impl.ui, javascript.debugger.backend (WebStorm), etc. — pass-2's module-descriptor-repository capsule covered the .dat/.jar REPOSITORY; this is the INTRA-JAR layout rule.

### Decisive source
```xml
<!-- generated descriptor: dependencies only, include LAST -->
<idea-plugin visibility="public" xmlns:xi="http://www.w3.org/2001/XInclude">
  <!-- region Generated dependencies - run `Generate Product Layouts` to regenerate -->
  <dependencies>
    <module name="intellij.platform.core"/>
    ... ×37 ...
  </dependencies>
  <!-- endregion -->
  <xi:include href="intellij.platform.debugger.impl.content.xml"/>
</idea-plugin>
<!-- content file: bare idea-plugin, no visibility attribute -->
<idea-plugin>
  <extensionPoints>...</extensionPoints>
  <extensions defaultExtensionNs="com.intellij">...</extensions>
</idea-plugin>
```

**Flow:** build tool regenerates the dependency block in place between region markers → human/tooling edits land only in `.content.xml` → at load time the platform splices the include so the module behaves as ONE descriptor → visibility comes from the OUTER file only.
**Invariant:** never add extensions to the generated file and never add `<dependencies>` to the content file; the include must be a relative same-jar href. Wrong port: merging into one file "for simplicity" — regeneration then destroys hand-written extensions on the next Product-Layouts run.
**Probe:** deterministic jar reads: `unzip -p lib/intellij.platform.debugger.impl.jar intellij.platform.debugger.impl.xml | grep -c '<module name='` → 37; `grep -c 'xi:include'` → 1; `unzip -p lib/intellij.platform.debugger.impl.jar intellij.platform.debugger.impl.content.xml | grep -c '<dependencies>'` → 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "debugger breakpoints pydevd", limit: 10, fields: ["signature", "name", "file"] });
```
(verified live: helpers-plane nodes resolve e.g. `AttachDebuggerTracing` ×2 line-exact; both descriptor files are jar-resident XML — retrieve by direct unzip, see Probe.)

## Verdict
Adopt generated-dependencies + XIncluded content split for any build-system that owns part of a manifest; adapt the include mechanism to your templating; omit IntelliJ's Product-Layouts generator. Coverage caveat: jar-resident XML read by unzip (`no_recorded_issue`, freshness `not_tracked`).
