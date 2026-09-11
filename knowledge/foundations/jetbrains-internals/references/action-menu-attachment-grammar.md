<!-- capsule-v2 -->
# Menu attachment grammar — how actions land in existing menus without owning them

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`intellij.python.community.impl.xml:1078-1302` inside `plugins/python-ce/lib/modules/intellij.python.community.impl.jar`); Codebase Memory `jetbrains-pycharm`. **Question:** What is the full positional grammar for injecting an action into a menu the plugin does not own — and what are the special anchors?

## add-to-group census (26 attachments in one module)
**Path/Symbol:** `intellij.python.community.impl.xml` — e.g. `:1117,1122,1134,1138,1142,1147,1151,1162,1168,1172,1177,1181,1188,1193,1198-1199,1204,1209-1211,1221-1222,1226,1237,1299-1300`.
**Signature:** `<add-to-group group-id="<existing-group-id>" anchor="first|last|before|after" [relative-to-action="<action-or-group-id>"]/>`; child-side variants: `<group id="X" [internal="true"] [popup="true|false"] [searchable="false"]>` and `<separator key="bundle.key"/>`.
**Data Shape:** anchors come in three families: absolute (`first`/`last`, no relative id), named-relative (`before`/`after` + platform action id like `NewFile`, `CompareClipboardWithSelection`, `ExtractMethod`, `StepInto`, `MarkSourceRoot`, `ProjectViewPopupMenuRefactoringGroup`), and bare attach (no anchor at all → unspecified position). Groups can be attached to MULTIPLE parents (one `<add-to-group>` per parent).

### Decisive source
```xml
<action id="NewPythonFile" class="...CreatePythonFileAction">
  <add-to-group group-id="NewGroup" anchor="before" relative-to-action="NewFile"/>       <!-- :1141-1143 -->
</action>
...
<action id="PyExtractFunction" class="...PyExtractFunctionAction"
        use-shortcut-of="ExtractMethod">                                                 <!-- :1196-1200 -->
  <add-to-group group-id="IntroduceActionsGroup" anchor="after" relative-to-action="ExtractMethod"/>
  <add-to-group group-id="Floating.CodeToolbar.Extract" anchor="first"/>                 <!-- TWO parents -->
</action>
```
Special forms observed: `use-shortcut-of="<action-id>"` borrows another action's keymap binding (:1197, :1203); `searchable="false"` on a group removes it from Search Everywhere/Cmd-Shift-A indexing (:1243); `<separator key="separator.python.packaging.settings"/>` gives even separators a bundle-localized label (:1090); `internal="true"` groups render only in internal-mode IDEs (:1230).

**Flow:** declaration registers action under global id → each `<add-to-group>` issues ONE attachment request against a group owned by someone else (platform menu or sibling toolwindow) → UI builds menus by resolving those ids at paint time.
**Invariant:** attachment is BY ID against foreign groups; the declaring plugin never mutates the host's descriptor. Wrong port: copying menu XML wholesale (forks the host menu), or assuming relative anchors auto-fall-back to first/last when the relative id vanishes (they degrade to unspecified — same degrade contract as extension-ordering-attributes).
**Probe:** deterministic: `unzip -p plugins/python-ce/lib/modules/intellij.python.community.impl.jar intellij.python.community.impl.xml | grep -c '<add-to-group '` → 26; `| grep -c 'use-shortcut-of='` → 2; `| grep -c 'searchable="false"'` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "smart step into instructions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt id-referenced declarative menu injection with three-family anchors; adapt group ids; omit IntelliJ's menu-update thread model. Coverage caveat: manifest read from jar.
