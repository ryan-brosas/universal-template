<!-- capsule-v2 -->
# host-widget-controllers — how do you programmatically drive deferred host widgets (dropdown menus, details fragments, button groups, notice banners) that only materialize their DOM on first interaction?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** When a menu's contents don't exist until opened (or a fragment loads lazily), what is the safe open→act→close sequence?

## withMenuOpen — click-driven lazy menu automation
**Path/Symbol:** `source/github-helpers/with-menu-open.ts:withMenuOpen` (:5–22); frame primitive `source/helpers/dom-utils.ts:frame` (:59–63).
**Signature:** `withMenuOpen<T>(menuButton: HTMLButtonElement, callback: (menu: HTMLElement) => T): Promise<T>`.
**Data Shape:** Generic return passthrough; throws if the labelled menu can't be found after opening; ALWAYS re-clicks to close in `finally`.

### Decisive source
```ts
menuButton.click();
// Wait for the menu DOM to be created, but not rendered
await frame(); // = new Promise(r => requestAnimationFrame(r))
try {
	// When executing concurrently, there might be multiple menus open…
	const menu = $(`[aria-labelledby="${menuButton.getAttribute('aria-labelledby') ?? menuButton.id}"]`);
	return callback(menu);
} finally {
	menuButton.click(); // toggle closed — no matter what
}
```

**Flow:** synthetic click → await exactly ONE animation frame (menu exists in DOM before paint) → locate the menu by ARIA: its `aria-labelledby` mirrors the button's own label/id → run callback synchronously inside try → close via second click even on throw.
**Invariant:** Menu identity is resolved through the ACCESSIBILITY tree (`aria-labelledby`), never sibling-position or `.open` classes — this survives concurrent menus and host redesigns. Callback must be sync (the menu is toggled shut in `finally` regardless); awaiting inside the callback races the close.
**Probe:** No direct unit test (host-DOM bound); caveat recorded. Consumers: features acting on dropdown items.

## loadDetailsMenu — force a deferred `<include-fragment>` to load on demand
**Path/Symbol:** `source/github-helpers/load-details-menu.ts:loadDetailsMenu` (:74–82).
**Signature:** `loadDetailsMenu(detailsMenu: HTMLElement): Promise<void>`.
### Decisive source
```ts
const fragment = $optional('.js-comment-header-actions-deferred-include-fragment', detailsMenu);
if (!fragment) return; // already loaded — nothing deferred left
detailsMenu.parentElement!.dispatchEvent(new Event('mouseover'));
await oneEvent(fragment, 'load');
```
**Flow:** detect the still-deferred fragment → synthesize `mouseover` on the PARENT (host listens there to start lazy loading) → resolve when the fragment fires `load`.
**Invariant:** The early-return-on-absence IS the "already loaded" signal — callers may call unconditionally. Event must target `detailsMenu.parentElement`, not the menu itself.
**Probe:** No direct test; caveat recorded.

## groupButtons / groupSiblings — Primer BtnGroup normalization
**Path/Symbol:** `source/github-helpers/group-buttons.tsx:groupButtons` + `groupSiblings` (:29–70).
**Flow:** ensure every button carries `BtnGroup-item` (unwrapping non-button wrappers by finding their inner `.btn`) → REUSE an ancestor `.BtnGroup` if one already wraps the first button, else create and `wrapAll` → add extra classes. `groupSiblings` walks previous/next `.btn` siblings to assemble the set.
**Invariant:** Joining an existing group beats creating nested groups — the closest-ancestor check comes BEFORE wrap. (No direct test.)

## addNotice — reuse the host's flash container
**Path/Symbol:** `source/github-helpers/notice-bar.tsx:addNotice` (:67–88).
**Flow:** `elementReady('#js-flash-container')` waits for the host banner root → append a Primer `flash flash-full flash-<type>` div with dismiss button.
**Invariant:** Notices ride the HOST's own container/classes so theme + stacking behave natively — never invent a parallel banner layer. Default action element is overridable with `action: false`. (No direct test.)

## Verdict
Adopt the interaction-driven reveal pattern (click → one rAF → aria-located act → finally-close; mouseover → await fragment load) for any lazy host widget. Adapt selectors, ARIA wiring, and class vocabularies to the target design system; keep the finally-close and parent-target event rules EXACTLY — they're the difference between automation and stuck UI.
