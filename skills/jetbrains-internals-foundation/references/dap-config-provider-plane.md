<!-- capsule-v2 -->
# DAP config-provider EP — run-configuration-to-debugger-protocol translation as declarative providers

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PRO module `plugins/python/lib/modules/intellij.python.jar:intellij.python.xml:77,119,162-163`; community module `plugins/python-ce/lib/modules/intellij.python.community.impl.jar`); Codebase Memory `jetbrains-pycharm`. **Question:** How does a framework-specific Run configuration get DEBUGGED without the debugger knowing every framework's launch semantics?

## debugpyConfigProvider census
**Path/Symbol:** `intellij.python.xml` — `<python.dap.run.debugpyConfigProvider implementation=.../>` at :77 (`FastApiRunConfigProvider`), :119 (`FlaskRunServerConfigProvider`), :162 (`CeleryRunAppConfigProvider`), :163 (`CeleryRunTaskConfigProvider`).
**Signature:** `<python.dap.run.debugpyConfigProvider implementation="<Provider FQN>"/>` under namespace `com.jetbrains.python` (EP owned by the python DAP module; consumed by PRO modules via `defaultExtensionNs="Pythonid"`-style custom namespaces and the dap module's own namespace).
**Data Shape:** each provider translates ONE configurationType's settings into debugpy/DAP launch parameters; one framework may ship TWO providers distinguishing entry modes (Celery: whole-app vs single-task). The community layer registers ZERO such providers — this plane is entirely in the PRO module.

### Decisive source
```xml
<configurationType implementation="com.intellij.python.pro.celery.configurations.CeleryRunConfigurationType"/>   <!-- :151 -->
...
<python.dap.run.debugpyConfigProvider implementation="com.intellij.python.pro.celery.debug.dap.CeleryRunAppConfigProvider"/>   <!-- :162 -->
<python.dap.run.debugpyConfigProvider implementation="com.intellij.python.pro.celery.debug.dap.CeleryRunTaskConfigProvider"/>   <!-- :163 -->
```

**Flow:** user Runs-with-debug a Celery/Flask/FastAPI configuration → platform resolves the programRunner chain (see run-config-type-runner-ordering) → the DAP layer looks up the registered provider for that configuration type → provider emits debugpy launch params → generic DAP runner attaches.
**Invariant:** translation is PER-TYPE and DECLARATIVE — the debugger core stays framework-ignorant. Wrong port: hard-coding per-framework launch logic inside the debugger, or assuming one provider per plugin (Celery needs two because app-run and task-run differ).
**Probe:** deterministic: `unzip -p plugins/python/lib/modules/intellij.python.jar intellij.python.xml | grep -c 'python.dap.run.debugpyConfigProvider'` → 4; same grep on community impl xml → 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "attach to process attach tracing", limit: 10, fields: ["signature", "name", "file"] });
```
(DAP bridge code IS indexed on the helpers plane: `plugins/python-ce/helpers/pydev/pydevd_attach_to_process/linux_and_mac/attach.cpp:102` AttachDebuggerTracing.)

## Verdict
Adopt per-type declarative translation from product-level run settings to a generic wire protocol; adapt the EP shape to your host's registry; omit debugpy itself. Coverage caveat: manifest read from jar.
