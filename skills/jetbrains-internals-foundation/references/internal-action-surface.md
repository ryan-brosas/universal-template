<!-- capsule-v2 -->
# Internal action surface — dev/internal-only commands as first-class registry entries

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (community `plugins/python-ce/lib/modules/intellij.python.community.impl.jar:intellij.python.community.impl.xml:1150-1152,1166-1169,1229-1238`; PRO `plugins/python/lib/modules/intellij.python.jar:intellij.python.xml:217-235`); Codebase Memory `jetbrains-pycharm`. **Question:** How does a product ship developer-only/maintenance actions so they are registered and scriptable but invisible to normal users?

## Internal/devmode census
**Path/Symbol:** community: `<action id="CleanPyc" ... >` with plain add-to-group (:1150), spellchecker dict regen into group `Internal` (:1166-1169), whole `<group id="Internal.Python" internal="true" popup="true" text="Python">` (:1230) attached via `<add-to-group group-id="Internal"/>` (:1237); PRO: `<group id="PyProjectViewGroup" internal="true" class="...NonTrivialActionGroup" popup="true">` hosting three `Devmode.*` actions (:219-232).
**Signature:** `<group id="X" internal="true" [popup="true"] [class="...ActionGroup"]>` + children `<action id= class= text= description= internal="true"/>`; attachment target is the PLATFORM's own `Internal` menu group.
**Data Shape:** 4× `internal="true"` per module; internal actions carry explicit `text`/`description` literals even inside bundled blocks (`<!--suppress PluginXmlI18n -->` comments mark the deliberate i18n bypass — these strings are never translated).

### Decisive source
```xml
<!--suppress PluginXmlI18n -->
<group id="Internal.Python" internal="true" popup="true" text="Python">
  <!--suppress PluginXmlI18n -->
  <action id="PyUpdateProjectSdk" internal="true" class="com.jetbrains.python.sdk.PyUpdateProjectSdkAction"
          text="Update Python SDK" description="Forcibly update all configured Python SDKs in the project"/>
  <add-to-group group-id="Internal"/>
</group>
```
PRO devmode twin: actions `Devmode.AnalyzeReturns` / `Devmode.AnalyzeTypeParser` / `Devmode.AnalyzeParameterTypes` under `internal="true"` group `PyProjectViewGroup` added to `ProjectViewPopupMenu` anchor="last".

**Flow:** declaration is IDENTICAL to normal actions → `internal="true"` marks visibility gating (rendered only when the IDE runs in internal mode, e.g. registry `ide.internal.enabled`) → maintenance tooling reaches them by id regardless.
**Invariant:** internal actions are REGISTERED like any other — keymaps/automation can invoke them by id even while hidden from menus; the i18n suppression is deliberate (maintenance strings stay English). Wrong port: hiding them by omitting registration entirely (breaks id-based invocation), or translating their literals.
**Probe:** deterministic: `unzip -p plugins/python-ce/lib/modules/intellij.python.community.impl.jar intellij.python.community.impl.xml | grep -c 'internal="true"'` → 4; `unzip -p plugins/python/lib/modules/intellij.python.jar intellij.python.xml | grep -c 'Devmode\.'` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "jupyter notebook kernel execution", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt register-everything + flag-gate-visibility for maintainer tooling; adapt the visibility flag to your host's debug-mode switch; omit IntelliJ's internal-mode registry details. Coverage caveat: manifest read from jar.
