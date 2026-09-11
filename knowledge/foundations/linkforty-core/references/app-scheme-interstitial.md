<!-- capsule-v2 -->
# Interstitial app-open page — scheme-then-store HTML with URL-fragment preservation through the handoff

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do you send a mobile visitor into an app via custom URI scheme without losing the fragment (E2E key) that a server never sees?

## generateInterstitialHTML — client-side scheme attempt, 1.5s store fallback, hash re-append
**Path/Symbol:** `src/routes/redirect.ts:generateInterstitialHTML` (:104-142); served from `handleRedirect` (:645-675) whenever `(device === 'ios' || device === 'android') && link.app_scheme`.
**Signature:** `function generateInterstitialHTML(schemeUrl: string, fallbackUrl: string, title?: string): string`.
**Data Shape:** Inputs escaped minimally (`"` → `&quot;`, `<` → `&lt;` for URLs; title also `>` → `&gt;`); scheme URL optionally carries deep_link_parameters appended with `?`/`&` awareness; `custom_scheme_url` column overrides the built `${app_scheme}://${deepPath}`.

### Decisive source
```html
<!-- redirect.ts:133-140 (inside template literal) -->
<script>
  // Preserve URL fragment (E2E encryption key) through the scheme redirect
  var hash = window.location.hash || '';
  var schemeUrl = "${safeSchemeUrl}" + hash;
  document.getElementById('open-btn').href = schemeUrl;
  window.location = schemeUrl;
  setTimeout(function() { window.location.replace("${safeFallbackUrl}"); }, 1500);
</script>
```

**Flow:** browser renders spinner page → JS reads `window.location.hash` (fragment never reaches the server, so it must be re-appended CLIENT-side onto the scheme URL) → navigates to scheme → if app absent the navigation fails silently and after 1500ms `location.replace(storeFallback)` fires, where `storeFallback` is picked browser-aware via `pickMobileFallbackUrl` (store-first regular / web-first in-app) falling back to `original_url`; manual buttons mirror both hops.
**Invariant:** The fragment MUST be appended by the page's own JS (server cannot know it); fallback uses `replace()` not assignment so back-button doesn't bounce users to the store; interstitial is only served when a store/web fallback exists (`if (storeFallback)` guard :662) else normal redirect path continues.
**Probe:** `bash -c "grep -cF 'window.location.hash' src/routes/redirect.ts"` → 2 (:100 doc comment + :135 code — count LINES not occurrences); `bash -c "grep -c '1500' src/routes/redirect.ts"` → 1 (:139); direct tests: none pin the HTML body — behavior seam covered by in-app-browser detection tests in `src/routes/redirect.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "interstitial scheme fallback app open", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fragment-preserving interstitial pattern for any custom-scheme handoff; adapt timing (1500ms) and styling; omit the E2E-key rationale if your fragments carry nothing sensitive — but keep client-side hash re-append regardless, since servers structurally cannot see fragments.
