<!-- capsule-v2 -->
# Boilerplate generator quartet — how does one plugin feed the New-Project wizard at three abstraction levels?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-webstorm`. **Question:** Which extension points turn a plugin into a project-template provider, and how do they compose?

## The wizard EP stack
**Path/Symbol:** `plugins/nodeJS/lib/nodeJS.jar:META-INF/plugin.xml:65-68`.
**Signature:**
```xml
<directoryProjectGenerator implementation="..."/>   <!-- per-template generator (2×) -->
<projectTemplatesFactory implementation="..."/>     <!-- grouped template list (1×) -->
<moduleBuilder builderClass="...FQN of a ModuleBuilder subclass"/>  <!-- module-level builder (1×) -->
```
**Data Shape:** nodeJS ships the full quartet: `NpmInitProjectGenerator` + `ExpressAppProjectGenerator` (directory generators — scaffold into an empty dir), `NodeTemplatesFactory` (groups templates incl. the Express entry for the Welcome screen), `ExpressAppProjectModuleBuilder` (module builder referenced BY CLASS NAME STRING via `builderClass=`, not by implementation bean).

### Decisive source
```xml
<directoryProjectGenerator implementation="com.jetbrains.nodejs.boilerplate.npmInit.NpmInitProjectGenerator" />
<directoryProjectGenerator implementation="com.jetbrains.nodejs.boilerplate.express.ExpressAppProjectGenerator" />
<projectTemplatesFactory implementation="com.jetbrains.nodejs.boilerplate.nodeBoilerplate.NodeTemplatesFactory" />
<moduleBuilder builderClass="com.jetbrains.nodejs.boilerplate.nodeBoilerplate.ExpressAppProjectModuleBuilder" />
```

**Flow:** Welcome screen → `projectTemplatesFactory` lists groups → user picks template → its `directoryProjectGenerator` scaffolds the directory (`npm init` shape or Express app) → if the project becomes a structured module, the matching `ModuleBuilder` (referenced by FQN string) drives module-level setup.
**Invariant:** one product feature may be exposed through MULTIPLE wizard EPs simultaneously (Express appears as both a directory generator and a module builder) — the EPs are complementary surfaces, not alternatives; `builderClass=` is indirection by name, so the class must exist at runtime or the entry silently vanishes.
**Probe:** `unzip -p plugins/nodeJS/lib/nodeJS.jar META-INF/plugin.xml | grep -c directoryProjectGenerator` → 2; `| grep -c projectTemplatesFactory` → 1; `| grep -c 'moduleBuilder '` → 1. Cluster corroboration for scale (reproducible census, same method as filetype-content-detector-plane): directoryProjectGenerator counts clion 25 / phpstorm 21 / rider 19 / rubymine 18 / pycharm 17 / rustrover 16 / webstorm 13 / goland 9 / dataspell 3 — every wizard-driven IDE feeds its New-Project flow this way (datagrip/mps ship none: no per-project scaffolding domain).

## Get live surrounding code
**Retrieve:** (jar-resident manifest plane — not symbol-indexed)
```bash
unzip -p plugins/nodeJS/lib/nodeJS.jar META-INF/plugin.xml | grep -E 'directoryProjectGenerator|projectTemplatesFactory|moduleBuilder'
```
ERRATUM (audit lane, pass 8): an earlier draft census in this block (ws 10 / py 12 / clion 20 / goland 10 / rider 16 / phpstorm 14 / rustrover 14 / rubymine 15 / dataspell 5) was FILE-level (`grep -l` over plugin.xml extracts), not tag-occurrence level — superseded by the Probe-line occurrence census above, which is the verified table.

## Verdict
Adopt: three-level wizard composition (dir-generator for plain scaffolds, factory for grouping/UI, module-builder-by-name for structured projects). Adapt generator implementations to your scaffolding stack. Omit the concrete npm/Express templates (product content).
