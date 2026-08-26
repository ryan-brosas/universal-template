<!-- capsule-v2 -->
# Inspection catalog registration — one tag = identity, i18n, severity, default

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PythonCore plugin); Codebase Memory `jetbrains-pycharm`. **Question:** What metadata makes a static-analysis rule addressable, suppressible, translatable and severity-groupable — in ONE declaration?

## localInspection
**Path/Symbol:** `plugins/python-ce/lib/*.jar:META-INF/plugin.xml` (106 `<localInspection language="Python" .../>` entries).
**Signature:** `<localInspection language="L" shortName="S" suppressId="SUP" bundle="messages.XBundle" key="INSP.NAME.k" groupKey="INSP.GROUP.g" enabledByDefault="true|false" level="ERROR|WARNING|WEAK WARNING" implementationClass="FQN"/>`.
**Data Shape:** shortName = stable tool id (profile persistence); suppressId = `#noinspection`/suppress-comment token; bundle+key+groupKey = externalized display strings; level = default severity; enabledByDefault = out-of-box state.

### Decisive source
```xml
<localInspection language="Python"
    shortName="PyUnusedLocalVariableInspection" suppressId="PyUnusedLocal"
    bundle="messages.PyPsiBundle" key="INSP.NAME.unused" groupKey="INSP.GROUP.python"
    enabledByDefault="true" level="WEAK WARNING"
    implementationClass="...inspections.unusedLocal.PyUnusedLocalVariableInspection" />
<inspectionElementsMerger implementation="...PyUnusedLocalVariableInspectionMerger" />
```

**Flow:** declare inspection with full metadata → profile UI groups by groupKey/bundle → engine runs class per file scope → findings suppressed via suppressId; mergers roll related inspections into one UI entry.
**Invariant:** the ID persisted in user profiles is `shortName` — renaming it orphans every saved profile that references it; suppression tokens must stay stable for the same reason. Wrong port: generating ids from class names (breaks when code moves).
**Probe:** deterministic: `grep -oE 'shortName="[^"]*"' py-plugin.xml | head -3` shows stable Py* ids distinct from class FQNs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "pydevd tracing settrace", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rich-metadata rule registration for any lint/analysis catalog; adapt severity ladder to your host; omit IntelliJ profile serialization internals. Coverage caveat: direct jar read; no test runner exists for installed builds.
