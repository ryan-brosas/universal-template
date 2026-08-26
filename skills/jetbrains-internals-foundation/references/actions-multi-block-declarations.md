<!-- capsule-v2 -->
# Multi-actions-block declarations — one plugin.xml may open `<actions>` several times with different i18n scopes

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`intellij.python.community.impl.xml:1078-1302` inside `plugins/python-ce/lib/modules/intellij.python.community.impl.jar`; PRO module `plugins/python/lib/modules/intellij.python.jar:intellij.python.xml:217-235`); Codebase Memory `jetbrains-pycharm`. **Question:** If `<actions>` carries a single optional `resource-bundle`, how do actions that need DIFFERENT bundles (or no bundle) coexist in one descriptor?

## Three sibling `<actions>` blocks in one module
**Path/Symbol:** `intellij.python.community.impl.xml` — block A `:1078-1105` (`<actions resource-bundle="messages.PyBundle">`, packaging toolwindow actions), block B `:1107-1240` (`<actions>` bare, debugger/console/refactoring), block C `:1242-1302` (`<actions>` bare, per-manager uv/poetry/hatch/conda/pip/pipenv group).
**Signature:** `<actions [resource-bundle="messages.X"]> ... </actions>` repeated at descriptor top level; child grammar identical in each block: `<action id class [icon] [internal="true"]>`, `<group id [popup] [searchable] [compact] [class]>`, `<add-to-group group-id anchor [relative-to-action]/>`, `<keyboard-shortcut keymap first-keystroke [second-keystroke] [replace-all]/>`, `<separator [key="bundle.key"]/>`.
**Data Shape:** the bundle attribute scopes to ITS block only — text-less actions in bundled blocks resolve keys against `messages.PyBundle`; bare blocks host actions whose texts come from code/annotations or platform defaults. PRO module shows the 1-block variant: one `<actions resource-bundle="messages.PythonProBundle">` (:217) holding internal devmode groups.

### Decisive source
```xml
<actions resource-bundle="messages.PyBundle">      <!-- :1078 -->
  <action id="PyInstallPackageAction" class="...PyInstallPackageAction"
          icon="AllIcons.ToolbarDecorator.Export">
    <keyboard-shortcut keymap="$default" first-keystroke="ctrl alt shift O"/>
  </action>
  ...
</actions>

<actions>                                           <!-- :1107, NO bundle -->
  <action overrides="true" id="ForceStepInto" class="...PyForceStepIntoAction"
          icon="AllIcons.Debugger.ForceStepInto"/>
  ...
</actions>

<actions>                                           <!-- :1242, NO bundle -->
  <group id="PythonPackageManagerActions" searchable="false">
    <separator/>
    <action id="UvLockAction" class="...UvLockAction" icon="com.intellij.icons.AllIcons.Diff.Lock"/>
    ...
    <add-to-group group-id="ExternalSystemView.ProjectMenu" anchor="last"/>
    <add-to-group group-id="RunContextGroup"/>
  </group>
</actions>
```

**Flow:** parser reads each `<actions>` block independently → bundle resolution is per-block → all declared actions/groups land in ONE global action registry keyed by id regardless of which block declared them.
**Invariant:** the registry is global; BLOCKS are just an i18n-scoping device. Wrong port: assuming one `<actions>` per file (misses half the registrations when porting by grep of the FIRST block), or applying the block's bundle to actions from other blocks.
**Probe:** deterministic: `unzip -p plugins/python-ce/lib/modules/intellij.python.community.impl.jar intellij.python.community.impl.xml | grep -c '<actions'` → 3; `| grep -c '<actions resource-bundle='` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "jupyter web action handler", limit: 10, fields: ["signature", "name", "file"] });
```
(action classes are compiled jar-resident; the graph's action-side hits live in the JS/web plane.)

## Verdict
Adopt repeatable declaration sections with locally-scoped i18n bundles feeding one global id-keyed registry; adapt bundling granularity; omit IntelliJ's action-update threading. Coverage caveat: manifest read from jar.
