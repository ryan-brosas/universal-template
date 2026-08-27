<!-- capsule-v2 -->
# safe-tab-options-open — how do you make tab creation and options-page opening safe across browsers, and enforce it mechanically?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** How does an extension guarantee that every `chrome.tabs.create` call goes through one per-browser-safe wrapper, that the options page opens from contexts that cannot open it directly, and that a regression is a BUILD error rather than a runtime surprise?

## Single choke point + restricted-syntax rule
**Path/Symbol:** `source/helpers/safe-create-tab.ts` — `safeCreateTab` :3–11 (whole file 11 lines); `eslint-rules/restricted-syntax.js` — `byo/prefer-safe-create-tab` :59–63; `source/helpers/open-options.tsx` — `openOptions` :4–7, `OptionsLink` :9–13 (whole file 13 lines); `source/background.ts` — `openOptionsPage` handler :59–63.
**Signature:** `safeCreateTab(properties: chrome.tabs.CreateProperties): Promise<chrome.tabs.Tab>`; `openOptions(event: Event | React.UIEvent, hash?: string): void`.

### Decisive source
```ts
// safe-create-tab.ts:
if (properties.openerTabId && isMobileFirefox()) {
	delete properties.openerTabId; // No support there https://stackoverflow.com/a/42422254
}
// eslint-disable-next-line byo/prefer-safe-create-tab -- Rule points to this function
return chrome.tabs.create(properties);
// eslint-rules/restricted-syntax.js:
'byo/prefer-safe-create-tab': ['error', {
	message: 'Import safeCreateTab instead',
	selector: 'CallExpression[callee.object.object.name="chrome"][callee.object.property.name="tabs"][callee.property.name="create"]',
}],
// open-options.tsx → background.ts:
void messageRuntime({openOptionsPage: hash ?? ''});
// ...
async openOptionsPage(hash: string) {
	return safeCreateTab({url: chrome.runtime.getURL(`assets/options.html${hash && `#${hash}`}`)});
},
```

**Flow:** any tab-opening need → content script either calls the background (`{openUrls}` / `{openOptionsPage: hash}`) or the background's own handlers run → ALL of them funnel through `safeCreateTab` → mobile-Firefox gets `openerTabId` deleted (unsupported there), every other browser passes properties through untouched → single `chrome.tabs.create` executes. Options deep-linking: `openOptions(event, id)` from a disabled-feature banner carries the feature id as hash; the background appends it only when non-empty.
**Invariant:** (1) exactly ONE `chrome.tabs.create` call site exists in the codebase — the restricted-syntax rule makes any other a lint ERROR (the wrapper's own disable comment "Rule points to this function" is the only legal exception); (2) the mobile-Firefox fix is property DELETION on a copy path, not an alternate API — all other `CreateProperties` pass through byte-identical; (3) options-page URL is built in the BACKGROUND via `chrome.runtime.getURL` — content scripts neither resolve extension asset URLs reliably nor may call `openOptionsPage`; (4) the hash travels as a plain string with `''` as the absent value (handler-side `hash && \`#${hash}\``), so the message shape never carries optional fields.
**Probe:** no direct unit test (browser-API-bound; standing caveat). Executed pins: `grep -n "isMobileFirefox|delete properties.openerTabId|chrome.tabs.create" source/helpers/safe-create-tab.ts` → 1, 5, 6, 10; `grep -n "prefer-safe-create-tab" eslint-rules/restricted-syntax.js` → 59, 62; `grep -n "safeCreateTab|openOptionsPage" source/background.ts` → 15, 44, 59, 60, 82, 105.
**Consumer evidence:** live `trace_path inbound safeCreateTab` → callers_total 4, ALL in background.ts (`openUrls`, `openOptionsPage`, `showWelcomePage`, action.onClicked handler). `search_code "openOptions"` → `rgh-options-link.tsx:19` (delegate click) + `disabled-feature-banner.svelte:66` (BannerAction with `hash=id` deep link). Sibling relationship: extension-ops-helpers.md owns the UX layer (≥10 confirm gate, toast rides the open promise); THIS capsule owns the platform-safety layer — deliberately a sibling, not a merge.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "safeCreateTab", direction: "inbound", limit: 25 });
// callers_total: 4 → background.openOptionsPage / openUrls / showWelcomePage (+action.onClicked)
```
Executed 2026-08-27 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the choke-point-plus-lint pattern for ANY privileged browser API with per-browser quirks: one wrapper, one restricted-syntax rule banning direct calls, wrapper carries the only disable. Adopt background-routed options opening (message with hash string, URL built via getURL in the worker). Adapt the quirk list (today: mobile-Firefox openerTabId) to your supported-browser matrix; omit the StackOverflow citation style if your house rules differ. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test — deterministic source pins + caller trace stand in.
