<!-- capsule-v2 -->
# Keymap shadow-entry resets — how does a foreign keymap UNBIND host shortcuts without empty attributes?

**Source:** JetBrains IDE distributions (proprietary distribution), pins as in leaf Provenance pass 10; Codebase Memory `jetbrains-rider` (resource plane, direct extraction). **Question:** When VSCode-style maps must REMOVE IntelliJ bindings they don't want, what is the mechanism — and why do naive attribute greps find nothing?

## Connected graph-selected seam
**Path/Symbol:** `rider/plugins/keymap-vscode/lib/keymap-vscode.jar` → `keymaps/VSCode.xml` (300 `<action>` entries; 195 keyboard-shortcut + 8 mouse-shortcut + 1 gesture).
**Signature:** self-closing shadow entry: `<action id="ActivateMessagesToolWindow" />` — an action element with an id but NO shortcut children.
**Data Shape:** 131 of 300 entries (43.7%) are pure shadows; the remaining 169 carry real bindings. Tag census: {action 300, keyboard-shortcut 195, mouse-shortcut 8, keyboard-gesture-shortcut 1}. The pass-6 `keymap-coverage-audit` capsule's "164 bound / 131 EMPTY resets" figure is CONFIRMED at this pin with refined grammar: "empty reset" = childless action element, NOT `first-keystroke=""` (zero such attributes exist). FORMATTING TRAP: only 129 of the 131 match `<action id="X" />` on one line — `ShowTypeBookmarks` and `RestoreDefaultLayout` omit the space (`<action id="ShowTypeBookmarks"/>`), so naive greps undercount by exactly the whitespace variants. The authoritative classifier is CHILD-COUNT between consecutive `<action>` opens, not string form.

### Decisive source
```xml
<!-- VSCode.xml — a pure shadow entry that erases the inherited binding -->
<action id="ActivateMessagesToolWindow" />
<!-- contrast: a bound entry -->
<action id="EditorChooseLookupItemReplace">
  <keyboard-shortcut first-keystroke="shift ENTER"/>
</action>
```

**Flow:** keymap resolution collects ALL matching action entries up the parent chain → a child entry with no shortcut children CONTRIBUTES NOTHING and thereby masks every ancestor binding for that id → net effect is deletion without any negative syntax → porters grepping for `first-keystroke=""` (or reading only bound entries) mis-measure the map.
**Invariant:** unbinding is expressed by PRESENCE of an action element with ABSENCE of children; the shadow must keep the exact action id. A map that wanted "inherit everything except X" is indistinguishable in file size from a full rebinding unless you count shadows.
**Probe:** `unzip -p $REFERENCE_ROOT/reference/jetbrains/rider/plugins/keymap-vscode/lib/keymap-vscode.jar keymaps/VSCode.xml | grep -c '<action id="[^"]*" />'` → 129 (the two no-space variants `…/>` are the remainder of 131; child-count classifier is authoritative); same pipe `| grep -c 'first-keystroke=""'` → 0.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", query: "keymap shortcut action", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: self-closing shadow entries as the unbind primitive and child-count as the bound/shadow classifier. Adapt to your host's override model. Omit JetBrains' specific choice set.
