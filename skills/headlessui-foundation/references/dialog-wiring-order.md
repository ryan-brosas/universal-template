<!-- capsule-v2 -->
# Dialog wiring order — which providers wrap the dialog, and what exactly shuts down when a Transition starts closing?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** In what order must Dialog compose its providers, and how do inert/scroll-lock/focus features react before the exit transition finishes?

## InternalDialog composition + isClosing demotion
**Path/Symbol:** `packages/@headlessui-react/src/components/dialog/dialog.tsx:121-348` (body), `:375-431` (DialogFn validation + Transition wrap), `:139-152` (role guard).
**Signature:** `Dialog({ open, onClose, initialFocus?, role='dialog', autoFocus=true, transition=false, unmount=false })` — throws when open/onClose missing or non-boolean/non-function.
**Data Shape:** context value `[{ dialogState, close, setTitleId, unmount }, { titleId, panelRef }]`; defaultContainer ref getter resolves `state.panelRef.current ?? internalDialogRef.current` lazily.

### Decisive source
```ts
return (
  <ResetOpenClosedProvider>            {/* stop Open/Closed leakage */}
    <ForcePortalRoot force={true}>     {/* ALWAYS portal, ignore outer group */}
      <Portal>
        <DialogContext.Provider value={contextBag}>
          <PortalGroup target={internalDialogRef}>
            <ForcePortalRoot force={false}>   {/* children may portal again */}
              <DescriptionProvider slot={slot}>
                <PortalWrapper>              {/* nested-portal registrar */}
                  <FocusTrap initialFocus={initialFocus} initialFocusFallback={internalDialogRef}
                             containers={resolveRootContainers} features={focusTrapFeatures}>
                    <CloseProvider value={close}>{render(...)}</CloseProvider>

// feature shutdown while closing:
let isClosing = usesOpenClosedState !== null ? (usesOpenClosedState & State.Closing) === State.Closing : false
let inertOthersEnabled = __demoMode ? false : isClosing ? false : enabled
let scrollLockEnabled = __demoMode ? false : isClosing ? false : enabled

// Escape handler blurs FIRST (Safari keeps focus+scroll otherwise):
if (document.activeElement && 'blur' in document.activeElement) document.activeElement.blur()
close()
```

**Flow:** DialogFn validates props → wraps InternalDialog in MainTreeProvider (+Transition if `transition`) → InternalDialog derives open from context when prop omitted → enabled = serverHandoffComplete && open → stackMachine push (top-layer) → outside-click/Escape (top-gated) → scroll lock → FocusTrap with computed features. Title/description ids flow upward via setTitleId/useDescriptions into aria-labelledby/describedby.
**Invariant:** the moment Closing is visible in context, inert + scroll-lock + InitialFocus DEMOTE immediately (not after transition ends) — this lets background content become interactive during exit animations without breaking focus restore; `role` silently coerces to 'dialog' with a one-time warn; Escape blurs activeElement BEFORE close to defeat Safari's scroll-to-focused-element.
**Probe:** deterministic ordering check against source JSX nesting (verified by reading render tree); direct tests: `dialog.test.tsx` Rendering suites (aria-modal only while open, title wiring), Keyboard suites (Escape closes; Tab locked), Mouse suites (outside click closes top layer).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "InternalDialog useDialogContext", limit: 5 });
```

## Verdict
Adopt the provider ORDER (Reset→ForcePortalRoot(true)→Portal→Context→PortalGroup→ForcePortalRoot(false)→…→FocusTrap→CloseProvider) — reordering breaks nested-portals and focus-guard placement; adapt provider names to your framework; omit __demoMode only if you lack a docs-screenshot use case.
