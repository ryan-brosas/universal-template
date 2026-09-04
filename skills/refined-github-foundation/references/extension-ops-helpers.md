<!-- capsule-v2 -->
# extension-ops-helpers — what operational micro-contracts govern version-gated behavior, tab fan-out confirmation, cache reset UX, and transient overlays?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** How does the extension encode release age, gate risky bulk actions, and give throwaway feedback without a UI framework?

## Version-as-release-date + platform-skewed staleness
**Path/Symbol:** `source/helpers/extension-release-age.ts:getExtensionReleaseDate` / `wasReleasedLongAgo` / `toDaysAgo` (:38–60); `source/helpers/is-development-version.ts:isDevelopmentVersion` (:61–65).
**Signature:** `getExtensionReleaseDate(): Date`; `wasReleasedLongAgo(releaseAgeInDays: number): boolean`.
### Decisive source
```ts
const maxReleaseAgeInDays = isSafari() ? 60 : 30; // Safari updates are less frequent
const [year, month, day] = version.split('.').map(Number);
// Version format: YY.M.D (e.g., 25.3.10 = 2025-03-10)
return new Date(2000 + year, month - 1, day);
// is-development-version.ts:
export default function isDevelopmentVersion(): boolean {
	return version === '0.0.0';
}
```
**Flow:** manifest version IS the ship date (calver YY.M.D) → parse into a Date (month −1, 0-based) → consumers compute days-ago and compare against the per-platform ceiling (30d store channel / 60d Safari). Dev builds (`0.0.0`) report "released today" so staleness gates never fire locally.
**Invariant:** The `2000 + year` offset and 0-based month are load-bearing calver assumptions — porting to semver versions breaks silently. Staleness gates (e.g. suppressing "report bug" prompts for outdated installs via `rgh-improve-new-issue-form.tsx:101`) must use the PLATFORM ceiling, not a constant.
**Probe:** No direct unit test (manifest-bound); caveat recorded.

## openTabs — confirm-before-fan-out through the background
**Path/Symbol:** `source/helpers/open-tabs.ts:openTabs` (:6–21).
**Signature:** `openTabs(urls: string[]): Promise<boolean>` (false = user aborted).
### Decisive source
```ts
if (urls.length >= 10 && !confirm(`This will open ${urls.length} new tabs. Continue?`)) return false;
const response = messageRuntime({openUrls: urls}); // background opens tabs
await showToast(response, {message: 'Opening…', doneMessage: pluralize(urls.length, '$$ tab') + ' opened'});
```
**Flow:** ≥10 URLs → native `confirm()` gate → delegate actual opening to the BACKGROUND worker (`{openUrls}` — content scripts can't reliably window.open N tabs without popup blocking) → toast rides the returned promise with loading→done messages.
**Invariant:** Tab OPENING happens in background (popup-blocker escape), but the CONFIRM stays in-page; abort must return `false` BEFORE messaging.
**Probe:** No direct test (confirm/messaging bound); receiver `background.openUrls` in graph.

## clearCacheHandler — button-self-destructing feedback
**Path/Symbol:** `source/helpers/clear-cache-handler.ts:clearCacheHandler` (:24–33).
**Flow:** `globalCache.clear()` → swap button text to 'Cache cleared!' + disable → restore original text/enabled after 2s.
**Invariant:** Feedback mutates the BUTTON ITSELF (no toast): original text captured before swap; handler doubles as an options-page action (`this: HTMLButtonElement`). (No direct test.)

## showOverlay — self-removing fullscreen notice
**Path/Symbol:** `source/helpers/overlay.tsx:showOverlay` (:5–18).
### Decisive source
```ts
await overlay.animate([{opacity: 1}, {opacity: 0}], {duration: 300, delay: 2000, easing: 'ease-in', fill: 'forwards'}).finished;
overlay.remove();
```
**Flow:** append `.rgh-overlay` div → Web Animations API fade-out after 2s delay → await `.finished` → remove node. **Invariant:** removal awaits the animation promise (`fill: 'forwards'` holds the faded state meanwhile) — no setTimeout race, no leaked overlay on early navigation since the node is only removed after its own animation completes. (No direct test.)

## abortableClassName — signal-scoped class lifecycle
**Path/Symbol:** `source/helpers/abortable-classname.ts:abortableClassName` (:4–9).
**Flow:** add classes → `onAbort(signal, () => remove them)` — class presence exactly tracks signal lifetime (TODO notes upstream abort-utils gap #12).
**Invariant:** Pairs with every `signal` passed to feature `init`s (see feature-loader-lifecycle.md): classes added under a run's signal vanish when that run aborts. (No direct test.)

## Verdict
Adopt the calver-as-date convention only if your release channel matches it; adopt unconditionally: ≥10 confirm + background-owned tab opening, in-button transient feedback, animation-promise-gated overlay removal, and signal-scoped class cleanup. Adapt thresholds, timing constants, and class names to your host.
