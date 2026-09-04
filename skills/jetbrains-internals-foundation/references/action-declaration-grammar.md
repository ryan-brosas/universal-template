<!-- capsule-v2 -->
# Action declaration grammar — how does PlatformActions.xml register actions, groups, references, and platform-default shortcuts?

**Source:** JetBrains IDE distributions (proprietary distribution), pin py 262.9437.214; Codebase Memory `jetbrains-pycharm` (resource plane, direct extraction). **Question:** What is the complete XML grammar a plugin author uses to declare an action and attach it to the menu/keymap system?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar` → `idea/PlatformActions.xml` (1,982 lines; siblings: idea/{ExecutionActions,LangActions,PriorityEditorLangActions,ProblemsViewActions}.xml in the same jar, META-INF/PlatformExecutionActions.xml + META-INF/VcsActions.xml in their own jars). Plugin equivalents live at `META-INF/plugin.xml <actions>` sections cluster-wide.
**Signature:** `<action id="X" class="f.q.Class" [icon="AllIcons.*"] [use-shortcut-of="OtherAction"]>` · `<group id="G" [popup="true"] [searchable="false"] [class="…EmptyActionGroup"] [icon=…]>` · `<add-to-group group-id="G" [anchor="first|last|before|after"] [relative-to-action="id"]/>` · `<reference ref="ExistingActionId"/>` · `<override-text place="EditorPopup" [text="…" key="…"]/>` · `<synonym key="action.X.synonym.y"/>` · `<abbreviation value="laf"/>` · `<separator key="…"/>`.
**Data Shape:** PlatformActions.xml census — 782 `<action>`, 198 `<group>`, 153 `<reference>`, 120 `<separator>`, 43 `<synonym>`, 38 `<add-to-group>`, 18 `<keyboard-shortcut>`, 15 `<override-text>`, 4 `<abbreviation>`, 3 `<mouse-shortcut>`. 113 `use-shortcut-of` occurrences; 13 inline `<keyboard-shortcut keymap="$default">` seeds (the Table/List families). Reserved grouping-only groups exist with `searchable="false"` and NO children (Other.KeymapGroup / Vcs.KeymapGroup / ProjectWidget.Actions) — pure keymap-settings buckets.

### Decisive source
```xml
<group id="Other.KeymapGroup" searchable="false"/> <!-- grouping for Settings -> Keymap -> Others -->

<action id="List-selectFirstRow" class="com.intellij.ui.ListActions$Home" use-shortcut-of="EditorTextStart"/>
<action id="Table-selectFirstRow" class="com.intellij.ui.TableActions$CtrlHome" use-shortcut-of="EditorTextStart">
  <keyboard-shortcut first-keystroke="control UP" keymap="$default"/>
</action>
<action id="CloseEditor" class="com.intellij.ide.actions.CloseEditorAction">
  <override-text place="EditorPopup"/>
  <override-text place="EditorTabPopup"/>
</action>
<reference ref="CompareClipboardWithSelection"/>
```

**Flow:** class-bound action declared with stable id → optionally borrows another action's bindings via `use-shortcut-of` → optional inline `<keyboard-shortcut keymap="$default">` seeds ONLY that named keymap (never all maps) → placement via add-to-group anchor or `<reference>` inside a group → per-place text overrides and search synonyms refine UX without touching the id.
**Invariant:** ids are global and immutable across the cluster (keymap files reference them by string); an inline shortcut without `keymap="…"` would leak into every map, which is why every inline binding observed carries explicit `keymap="$default"` or a mac name. `searchable=false` removes a group from Go-To-Action search while keeping it functional.
**Probe:** `unzip -p $REFERENCE_ROOT/reference/jetbrains/pycharm/lib/intellij.platform.ide.impl.jar idea/PlatformActions.xml | grep -c '<action ' ` → 782; same pipe `| grep -c 'use-shortcut-of'` → 113; `grep -c 'keymap="\$default"'` → 13.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "action group menu registration", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the full declaration grammar (id/class/use-shortcut-of/override-text/synonym/abbreviation/reference/add-to-group anchors) and keymap-scoped inline defaults. Adapt icon vocabulary to your host. Omit the specific 782-action platform catalog.
