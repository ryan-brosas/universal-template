<!-- capsule-v2 -->
# background-message-router — how do content scripts delegate privileged work to an MV3 service worker without global tab state?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** How is the background↔content-script protocol shaped so tab operations and proxied fetches stay correct and keep the host page console clean?

## Declarative handler map with sender-bound tab operations
**Path/Symbol:** `source/background.ts` — `handleMessages({...})` (:38–67): `ping` :39–41, `openUrls` :42–50, `closeTab` :51–53, `fetchText` re-export :54, `fetchJson` :55–58, `openOptionsPage` :59–63, `getStyleHotfixes` :64–66.
**Signature:** `handleMessages(handlers)` from `webext-msg`; every handler `async`, keyed by request type; tab-touching handlers take a second `(payload, {tab}: chrome.runtime.MessageSender)` parameter.
**Data Shape:** request = `{<handlerName>: payload}` object; response = handler return value. Sender context is authoritative for tab identity.

### Decisive source
```ts
async openUrls(urls: string[], {tab}: chrome.runtime.MessageSender) {
	for (const url of urls) {
		void safeCreateTab({url, openerTabId: tab!.id, active: false});
	}
},
async closeTab(_: any, {tab}: chrome.runtime.MessageSender) {
	void chrome.tabs.remove(tab!.id!);
},
```

**Flow:** content script calls `messageRuntime({closeTab: true})` → webext-msg routes by key to the background handler → handler derives the target tab EXCLUSIVELY from `MessageSender.tab` → fire-and-forget (`void`) so the reply isn't blocked on tab creation/removal.
**Invariant:** there is NO global "current tab" state anywhere in the background; concurrent callers each act on their own sender tab. Tab-opening lives in the worker (popup-blocker escape hatch), while user confirmation stays page-side (see extension-ops-helpers.md openTabs).
**Probe:** no direct unit test exists for `background.ts` (service-worker-bound; repo tests cover pure helpers only — standing caveat). Executed deterministic pins: `grep 'handleMessages|openerTabId|chrome.tabs.remove|getStyleHotfixes|welcomeShown.set\(true\)|isDevelopmentVersion\(\)|globalCache.clear' source/background.ts` → lines 38, 46, 52, 64, 108, 113, 114.

## Console-hygiene proxy + install lifecycle
**Path/Symbol:** `source/feature-manager.tsx:globalReady` consumer at :121 (`void messageRuntime<string>({getStyleHotfixes: true}).then(applyStyleHotfixes)`); lifecycle tail `source/background.ts:showWelcomePage` :88–110 + `onInstalled` :112–119.
### Decisive source
```ts
// Request in the background page to avoid showing a 404 request in the console
// https://github.com/refined-github/refined-github/issues/6433
void messageRuntime<string>({getStyleHotfixes: true}).then(applyStyleHotfixes);
// background.ts:
try { … } finally {
	// Make sure it's always set to true even in case of errors
	await welcomeShown.set(true);
}
```
**Flow:** hotfix CSS strings are fetched in the WORKER (a missing CSV would 404 invisibly there instead of printing in the host page console, #6433) and pushed to whichever content script asks. Install path: dev version (`0.0.0`) clears `globalCache` first, then `showWelcomePage()` double-checks stored token + GitHub origin permission before opening the welcome tab, and latches `welcomed=true` in a `finally`.
**Invariant:** one-shot UX latches must be set even when their side effect fails (no infinite welcome loop across updates); cache reset precedes permission-sensitive flows because Safari can lose base permissions during reinstall (upstream comment).
**Probe:** same executed grep set (lines 108, 113, 114 above); consumer pin via live `search_code getStyleHotfixes` returning exactly `background.ts:64-66` + `feature-manager.globalReady` (:121 hit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", qn_pattern: "refined-github\\.source\\.background\\..*", fields: ["lines", "signature"] });
// total: 10 — ping 39-41, openUrls 42-50, closeTab 51-53, fetchJson 55-58,
// openOptionsPage 59-63, getStyleHotfixes 64-66, showWelcomePage 88-110, vars 20/22
```
Executed 2026-08-26 @ pin 3187161.

## Verdict
Adopt the declarative message-map protocol, sender-derived tab identity, worker-side proxied fetches, and failure-proof one-shot latches. Adapt handler vocabulary and welcome/token policy to your host. Omit the GHE permission toggle wiring (`webext-permission-toggle`) unless you target arbitrary origins. Coverage caveat: all 15 batch paths `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no direct tests exist for this file — probes are source pins.
