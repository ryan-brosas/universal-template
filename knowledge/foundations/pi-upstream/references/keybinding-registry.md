<!-- capsule-v2 -->
# Keybinding registry — how do you make rebinding keys non-breaking and self-documenting?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter hard-codes key handlers and every rebind forks component logic — what registry shape avoids that?

## Semantic action ids + description metadata; components bind to actions
**Path/Symbol:** `packages/tui/src/keybindings.ts` (320L).
**Signature:** ~40 semantic action ids (`tui.editor.deleteWordBackward`, `tui.altScreen.searchNext`, …), each with a default key list plus a human description; downstream packages extend the action space via TypeScript DECLARATION MERGING on the `Keybindings` interface.
**Data Shape:** Every binding = {actionId, keys[], description}. Emacs/readline duality honored by DEFAULT: arrows AND ctrl+b/f/n/a/e; word motion gets alt+arrow, ctrl+arrow, AND alt+b/f — three muscle-memory families simultaneously. Deliberately EMPTY default arrays (`historyPrevious/historyNext: []`) ship features unbound until configured.

### Decisive source
```ts
// Components bind to ACTIONS, never raw keys:
//   tui.editor.deleteWordBackward  → ["alt+backspace", "ctrl+w"]
//   tui.historyPrevious            → []          // opt-in until configured
// Extensibility through the type system:
declare module "./keybindings.ts" { interface Keybindings { myExtensionAction: ... } }
```
Every binding carries a human description, so settings/help surfaces generate themselves from the registry.

**Flow:** keypress → resolve through user overrides → defaults → action id → dispatch to whichever component registered interest in that action. Rebinds change only the registry entry.
**Invariant:** No component may test raw key values — behavior is keyed by semantic action id so rebinding can never fork logic; an empty default array is a FEATURE FLAG (unbound ≠ broken).
**Probe:** `packages/tui/test/keybindings.test.ts` (matchesKey round-trips).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "Keybindings action ids default", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt action-id registries with descriptions and intentional empty bindings. Adapt ids to your feature names. Omit declaration-merging if your host isn't TypeScript. Coverage caveat: none.
