<!-- capsule-v2 -->
# Command-menu manifest registry — how does a ⌘K palette host entries whose copy and existence belong to an external manifest?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How should palette items resolve copy (i18n key vs manifest literal), disappear when their feature is unadmitted, and treat keyboard vs pointer interaction differently?

## Manifest-owned copy + two-element action duality
**Path/Symbol:** `src/components/features/command-menu/command-menu-items.tsx` (`CommandMenuItemDefinition` :54–68, `commandMenuItemCopy` :74–81, `createCommandMenuItems` :95–214 — automations entry :118–132); `src/components/features/command-menu/command-menu.tsx` (`matchesQuery` :34–58, keyboard grammar :153–182, anchor-vs-button :337–380).
**Signature:** `commandMenuItemCopy(literal: string | undefined, key: I18nKey | undefined, translate): string`; items are `{ id, group, titleKey?/title?, descriptionKey?/description?, keywordsKey?/keywords?, icon, to?, perform? }`.
**Data Shape:** typed `CommandMenuItemId` union + `COMMAND_MENU_ROUTE` const routes; groups rendered in fixed order navigation→settings→actions, empty groups skipped.

### Decisive source
```ts
// command-menu-items.tsx — the automation interface owns this entry's copy,
// so an ABSENT manifest leaves the command menu without it rather than with
// host copy.
...(hasAutomationInterface()
  ? [{ id: "automations" as const, group: "navigation" as const,
       title: getInterfaceCopy().commandMenuTitle, … }]
  : []),
```
```ts
// command-menu.tsx — `to` items render as <a href> so modifier-clicks keep
// browser semantics; the early return happens BEFORE preventDefault.
onClick={(event) => {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }
  event.preventDefault();
  runItem(item);
}}
```

**Flow:** global meta/ctrl+k opens via window listener; on open rAF-focuses the input; `matchesQuery` = AND-of-terms substring over title+description+keywords resolved THROUGH `commandMenuItemCopy` (literal-over-key precedence ⇒ manifest-owned items search by THEIR words); active index clamped by an effect to `[0, filtered.length)` or -1 when empty; ArrowUp/Down wrap modulo filtered length, Enter runs, Escape closes; `runItem` closes FIRST then either `navigate(item.to)` or `item.perform()`; close resets query/index/option-ref map. ARIA combobox/listbox/option with `aria-activedescendant`, `scrollIntoView({block:"nearest"})`.
**Invariant:** A feature's palette presence is decided by its manifest admission, never by a fallback label owned by the host app. Copy resolution is one function used identically for rendering AND search. Modifier-clicks must preserve browser link behavior; plain clicks navigate in-app. Local actions (`perform`) render as buttons, routes as anchors.
**Probe:** `__tests__/components/features/command-menu/command-menu-items.test.tsx` (25 L) — absent manifest omits automations, keeps the rest; `__tests__/components/features/command-menu/command-menu.test.tsx` (149 L) — cmd/ctrl+k open + Escape close (:50–77), keyword filtering (:79–90), navigate-and-close (:92–102), arrow+enter selection (:104–118), perform actions mutate sidebar store (:120–131). Flagged parse-partial lines (:27/:12) are `importOriginal<typeof import(…)>()` scaffolding — read directly, benign.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "command menu items manifest interface copy palette", limit: 10 });
```

## Verdict
Adopt the literal-over-key copy resolver shared by render and search, admission-gated entry construction, and the anchor/button action duality with modifier passthrough. Adapt the group taxonomy and shortcut set; omit the manifest system if your features are compile-time fixed. Coverage: no_recorded_issue on all cited paths at gen 2026-08-24T16:13:32Z (two test files carry benign importOriginal parse-partial flags, read directly).
