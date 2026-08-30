<!-- capsule-v2 -->
# Mobile redirect fallback chain — which URL wins for ios/android/web, and how does browser type reorder the store-vs-web fallback?

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** When a short-link click arrives, what ordered chain picks the destination URL per device, and why does an in-app browser swap store-first for web-first?

## iOS/Android priority ladder + browser-aware fallback picker
**Path/Symbol:** `src/routes/redirect.ts:handleRedirect` (device ladder :553-599) + `src/routes/redirect.ts:pickMobileFallbackUrl` (:73-94) + `src/routes/redirect.ts:isIOSInAppBrowser` (:19-32) / `isAndroidInAppBrowser` (:39-56).
**Signature:** `function pickMobileFallbackUrl(device: 'ios' | 'android', userAgent: string, iosUrl: string | null, androidUrl: string | null, webFallbackUrl: string | null): { url: string; reason: string } | null`.
**Data Shape:** Per-device URL inputs resolved first through the three-level fallback chain `link column → template_settings.default*Url → org_settings.appConfig.*` (:549-551); output carries a machine-readable `reason` (`ios_app_store_url` | `android_app_store_url` | `web_fallback_url`); `null` means caller falls back to `original_url`.

### Decisive source
```ts
// redirect.ts:86-92 — the ONLY difference between browser classes:
if (inApp) {
    if (webFallbackUrl) return { url: webFallbackUrl, reason: 'web_fallback_url' };
    if (storeUrl)       return { url: storeUrl,       reason: storeReason };
} else {
    if (storeUrl)       return { url: storeUrl,       reason: storeReason };
    if (webFallbackUrl) return { url: webFallbackUrl, reason: 'web_fallback_url' };
}
```

**Flow:** device = `detectDevice(ua)` → ios: 1) `ios_universal_link`, 2) `app_scheme://deep_link_path`, 3) `pickMobileFallbackUrl(...)`, 4) `original_url`; android mirrors with `android_app_link`; web: `web_fallback_url || original_url`. Inside step 3, regular browsers prefer the Store URL (OS-level UL/App-Link check already ran and didn't fire ⇒ app not installed); in-app browsers (GSA/Gmail/FBAN|FBAV/Instagram/Twitter/LinkedIn/MicroMessenger/Outlook/YahooMobile on iOS; FB_IAB/Line/KAKAOTALK/WhatsApp/Pinterest/Telegram/Snapchat/`\swv)` WebView marker on Android) prefer the web fallback because UL was bypassed regardless of install state, and a fallback on the app's UL domain gives the OS a second chance to fire.
**Invariant:** The reorder applies ONLY at fallback step 3 — Universal Link / App Link / app_scheme always outrank both store and web URLs for every browser class; `pickMobileFallbackUrl` returning `null` must fall through to `original_url`, never 404.
**Probe:** `bash -c "grep -cF 'UL was bypassed; web fallback gives UL a second chance to fire' src/routes/redirect.ts"` → 1 (:565); direct tests `src/routes/redirect.test.ts` describe('isIOSInAppBrowser')/'isAndroidInAppBrowser' + `pickMobileFallbackUrl` cases pin Gmail/GSA, FBAN, WebView-marker detection and both orderings.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "pickMobileFallbackUrl in-app browser store fallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-step device ladder, the three-level URL resolution chain (link → template → org), and the in-app-browser store/web swap with its `reason` labels; adapt UA-pattern lists to your traffic mix; omit LinkForty-specific column names only if you rename coherently on BOTH the SQL select and the JSON cache row.
