<!-- capsule-v2 -->
# Optional-depends config-file fragment — how does a bundled plugin ship capability code that loads only when its host product has the feature?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-webstorm`. **Question:** How do you split a plugin's extensions so a subsystem (e.g. coverage) activates only when the host IDE provides it, instead of hard-failing on load?

## The `<depends optional="true" config-file="...">` split
**Path/Symbol:** `plugins/nodeJS/lib/nodeJS.jar:META-INF/plugin.xml:46` (`<idea-plugin>` dependencies block) + `META-INF/nodejs-coverage.xml` (whole 10-line fragment).
**Signature:** `<depends optional="true" config-file="<fragment>.xml"><module-or-plugin-id></depends>` — the referenced file sits NEXT TO plugin.xml inside the same jar.
**Data Shape:** main descriptor = always-loaded core (12 `<module name=.../>` deps + 6 `<depends>`, incl. `com.intellij.modules.ultimate`; run/test/profile services at :53-92). Fragment = `<idea-plugin>` root holding ONLY feature-gated contributions: `MochaCoverageProgramRunner` (programRunner), `MochaCoverageEngine` (coverageEngine), `MochaCoverageRunner` (coverageRunner), `MochaCoverageAnnotator` (projectService).

### Decisive source
```xml
<depends optional="true" config-file="nodejs-coverage.xml">com.intellij.modules.coverage</depends>
```
```xml
<!-- META-INF/nodejs-coverage.xml (fragment root is <idea-plugin>, no id/version) -->
<extensions defaultExtensionNs="com.intellij">
  <programRunner implementation="com.jetbrains.nodejs.mocha.coverage.MochaCoverageProgramRunner"/>
  <coverageEngine implementation="com.jetbrains.nodejs.mocha.coverage.MochaCoverageEngine"/>
  <coverageRunner implementation="com.jetbrains.nodejs.mocha.coverage.MochaCoverageRunner"/>
  <projectService serviceImplementation="com.jetbrains.nodejs.mocha.coverage.MochaCoverageAnnotator"/>
</extensions>
```

**Flow:** container parses plugin.xml → hits optional depends → probes host for `com.intellij.modules.coverage` → present: loads fragment from same jar dir and merges its extensions; absent: skips silently (no error, core plugin fully functional minus coverage).
**Invariant:** the fragment must stay self-sufficient (own `<idea-plugin>` root, no references back into unloaded classes); everything a missing module would break lives in the fragment, never in the main descriptor. Wrong port: putting feature code in the main file "guarded by an if" — there is no runtime guard; the split IS the mechanism.
**Probe:** `unzip -p plugins/nodeJS/lib/nodeJS.jar META-INF/plugin.xml | grep -c 'optional="true" config-file='` → 1; `unzip -p plugins/nodeJS/lib/nodeJS.jar META-INF/nodejs-coverage.xml | grep -c '<programRunner '` → 1. Cluster corroboration (reproducible tag-aware census over `<depends>` elements carrying BOTH `optional="true"` and `config-file=`, 11 installs — attr-order/multiline-safe): **114** declarations cluster-wide — phpstorm 23 / webstorm 17 / rider 11 / rubymine 12 / phpstorm-light 19 / rustrover 6 / pycharm 5 / dataspell 7 / clion 5 / goland 2 / mps 7 / datagrip 0.

## Get live surrounding code
**Retrieve:** (jar-resident manifest plane — not symbol-indexed)
```bash
unzip -p plugins/nodeJS/lib/nodeJS.jar META-INF/nodejs-coverage.xml
```
The graph's code plane covers helper scripts only; retrieve manifest seams by direct unzip (see Probe).

## Verdict
Adopt: optional-depends fragment split for any plugin whose feature set must degrade gracefully when a host capability is absent (the platform's own feature-flag-at-descriptor-level). Adapt the probe key (`com.intellij.modules.*` vs plugin ids) to your container's dependency vocabulary. Omit IntelliJ's specific coverage engine trio (domain logic). Complements product-fragment-wiring (product-level composition) — this is the capability-level cut INSIDE one plugin.
