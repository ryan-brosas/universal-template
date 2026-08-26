<!-- capsule-v2 -->
# Plugin-declared keymap defaults — why do plugin.xml files carry inline keyboard-shortcuts scoped to named keymaps?

**Source:** JetBrains IDE distributions (proprietary distribution), pins as in leaf Provenance pass 10; Codebase Memory `jetbrains-*` (resource plane, direct extraction). **Question:** When a plugin needs a shortcut, does it edit keymaps or declare its own default — and what is the scoping rule?

## Connected graph-selected seam
**Path/Symbol:** `META-INF/plugin.xml <actions>` sections across all 15 installs; richest instances: `pycharm/plugins/jupyter-plugin/lib/jupyter-plugin.jar` (66 inline `<keyboard-shortcut>`), `<prod>/plugins/terminal/lib/terminal.jar` (53 in EVERY 262 IDE), `rider/plugins/dotCover/lib/dotCover.jar` (22).
**Signature:** `<action id="P" class="…"><keyboard-shortcut first-keystroke="K" keymap="$default"/>[<keyboard-shortcut first-keystroke="meta K" keymap="Mac OS X"/>][<override-text place="GoToAction"/>]</action>`.
**Data Shape:** cluster census (descriptors with ≥1 action): pycharm 73 descriptors / 1,484 actions / 236 inline shortcuts · webstorm 69 / 2,797 / 220 · rider 87 / 1,622 / 188 · datagrip 32 / 2,423 / 194 · clion 77 / 1,492 / 166 · phpstorm 74 / 1,323 / 166 · rubymine 65 / 1,309 / 172 · rustrover 60 / 1,253 / 151 · goland 60 / 1,339 / 149 · psl 59 / 1,195 / 145 · dataspell 36 / 1,010 / 239 · mps 16 / 336 / 81 · air / dotmemory / dottrace 0 (no action system). Terminal.jar's plugin.xml is 502 lines whose ONLY cross-install diff is the version/since/until stamp trio; terminal carries 22 `keymap="$default"` + explicit mac-name bindings.

### Decisive source
```xml
<!-- terminal.jar plugin.xml — platform-default seed plus mac-name seeds -->
<action id="Terminal.InsertInlineCompletion" class="com.intellij.terminal.frontend.action.TerminalInsertInlineCompletionAction">
  <keyboard-shortcut first-keystroke="RIGHT" keymap="$default" />
  <override-text place="GoToAction" />
</action>
<action id="Terminal.ClearBuffer" class="com.intellij.terminal.frontend.action.TerminalClearAction">
  <keyboard-shortcut first-keystroke="meta K" keymap="Mac OS X" />
  <keyboard-shortcut first-keystroke="meta K" keymap="Mac OS X 10.5+" />
</action>
```

**Flow:** plugin declares action + its OWN preferred defaults inside its descriptor → each named keymap absorbs the binding as if shipped with the map → users overriding later always win → mac coverage requires naming EACH mac map separately (Mac OS X AND Mac OS X 10.5+), because `$default` is not their ancestor-of-record for absorption semantics.
**Invariant:** an inline shortcut NEVER applies to all keymaps — it lands only in the explicitly named one(s); omitting the attribute would be a grammar violation observed zero times across the FULL cluster census of 2,107 inline `<keyboard-shortcut>` entries (all descriptors, all 15 installs, verified by attribute scan). This is how plugins ship sensible defaults without mutating shared resources.
**Probe:** `unzip -p /mnt/hdd/utopia/inspo/reference/jetbrains/pycharm/plugins/terminal/lib/terminal.jar META-INF/plugin.xml | grep -c 'keymap="\$default"'` → 22; `unzip -p … same jar … | grep -c '<keyboard-shortcut'` → 53.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "terminal action shortcut", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: descriptor-owned default bindings with per-keymap explicit scoping and separate mac-map seeding. Adapt to your host's equivalent plugin manifest. Omit JetBrains' specific bindings.
