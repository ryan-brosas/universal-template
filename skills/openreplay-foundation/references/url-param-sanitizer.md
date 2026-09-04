<!-- capsule-v2 -->
# URL query-param sanitizer — which default params are masked in page locations and how does hash-router rewriting interact?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** How do you scrub tokens from URLs while keeping SPA hash routes replayable?

## Lowercase-key allowlist masking + optional `#/` stripping
**Path/Symbol:** `tracker/tracker/src/main/modules/viewport.ts` — `defaultUrlSanitizer` (:6–19), `replaceHashSymbol` handling (:44–51), privateMode title/url/referrer wipe (:52–57), ticker wiring (:98–99).
**Signature:** `defaultUrlSanitizer(url: string): string`; option `replaceHashSymbol?: boolean` applied BEFORE sanitizers.
**Data Shape:** hidden params: `jwt, password, reset-password, invitation, secret, token` (case-insensitive); value replaced with same-length stars; parse failures return input unchanged.

### Decisive source
```ts
const hiddenQueryParams = ['jwt','password','reset-password','invitation','secret','token']
u.searchParams.forEach((value, key) => {
  if (hiddenQueryParams.includes(key.toLowerCase())) {
    u.searchParams.set(key, '*'.repeat(value.length))
  }
})
```
```ts
// '#/path' → '/path' so the player sees a normal router URL
const routePath = hashRoute ? '/' + u.hash.replace(/^#\/+/, '') : ''
url = u.origin + u.pathname.replace(/\/$/, '') + routePath + u.search
```

**Flow:** on each tick compare document.URL → changed ⇒ optionally rewrite hash-route → sanitize query params (star-mask) → under privateMode also wipe title/referrer via stringWiper → send SetPageLocation with timeOrigin-based navigation start.
**Invariant:** Hash stripping happens BEFORE sanitization (order is documented in-source) and must not affect `location` itself — only the recorded copy. Masking preserves parameter presence but not its secrecy-critical value length? No — it PRESERVES length by design (`'*'.repeat(value.length)`), only hiding content.
**Probe:** `grep -c "hiddenQueryParams = \['jwt', 'password', 'reset-password', 'invitation', 'secret', 'token'\]" tracker/tracker/src/main/modules/viewport.ts` → `1`; `grep -c "hash.startsWith('#/')"? tracker/tracker/src/main/modules/viewport.ts` → see probe below; direct tests: none upstream for viewport sanitizer beyond suite compile (coverage caveat).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "defaultUrlSanitizer hiddenQueryParams replaceHashSymbol", limit: 10 });
```

## Verdict
Adopt lowercase allowlist star-masking. Adapt the param list to your threat model. Omit hash rewriting when your router uses path URLs.
