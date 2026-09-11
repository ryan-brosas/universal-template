<!-- capsule-v2 -->
# Bot detection & proxy gate — how do you distinguish link previews/scrapers from real users at the edge, and why do bots get a rewrite instead of a redirect?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** What signals classify a request as a bot (with what false-positive guards), and what does the edge serve them when social-preview metadata is enabled?

## detectBot multi-signal + bot→proxy rewrite branch
**Path/Symbol:** `apps/web/lib/middleware/utils/detect-bot.ts:detectBot` (11-63); consumer `apps/web/lib/middleware/link.ts:314` + branch `:323-335`; lists `apps/web/lib/middleware/utils/bots-list.ts` (`UA_BOTS`, `IP_BOTS`, `IP_RANGES_BOTS`, `REFERRER_BOTS`).
**Signature:** `detectBot(req: Request): boolean`.
**Data Shape:** signal priority: explicit `?bot=` param → HEAD method → User-Agent (`ua.isBot` OR fragment list, after false-positive scrub) → referer regex → exact IP set → CIDR ranges. False-positive guard: `UA_FALSE_POSITIVES = [/Google\/google\b/]` (Instagram in-app webview on Pixels embeds "Google/google" in its device descriptor).

### Decisive source
```ts
if (searchParams.get("bot")) return true;        // manual override
if (req.method === "HEAD") return true;          // "real users always use GET"
const ua = userAgent(req);
if (ua) {
  const isKnownFalsePositive = UA_FALSE_POSITIVES.some((p) => p.test(ua.ua));
  const sanitizedUa = UA_FALSE_POSITIVES.reduce(
    (s, p) => s.replace(p, ""), ua.ua);
  return (!isKnownFalsePositive && ua.isBot) ||
         UA_BOTS.some((bot) => new RegExp(bot, "i").test(sanitizedUa));
}
// then: referer regex → IP_BOTS.includes(ip) → IP_RANGES_BOTS.some(isIpInRange)
```
```ts
// link.ts — bots get HTML with OG tags via REWRITE, humans get REDIRECT
if (isBot && proxy) {
  return createResponseWithCookies(
    NextResponse.rewrite(
      new URL(`/${domain}/${encodeURIComponent(key)}/proxy`, req.url), {/* ... */}),
    cookieData,
  );
}
```

**Flow:** cheap deterministic signals first (param/method) → UA with false-positive scrub → network-level signals last. When bot ∧ `proxy` enabled, middleware rewrites (same-origin fetch of `/[domain]/[key]/proxy`) so the scraper sees server-rendered Open-Graph metadata for the DESTINATION while the browser URL stays the short domain.
**Invariant:** detection is read-only and never blocks — bots still get a 200 response (the proxy page), not 403; abuse control is separate from preview rendering. The false-positive regex must run BEFORE both `ua.isBot` and the fragment match, else legit in-app browsers are misclassified. Rewrite-not-redirect is required: a redirect would leak the destination URL into the scraper's result card.
**Probe:** no upstream unit test (coverage caveat). Deterministic probe: `HEAD` request → true; UA containing "Google/google" (Pixel Instagram webview pattern) → false despite generic "google" entry; `?bot=1` → true regardless.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "detectBot UA_BOTS IP_RANGES_BOTS proxy rewrite", limit: 10 });
```

## Verdict
Adopt: ordered cheap-to-expensive signals, false-positive sanitization before classification, and the bot→same-origin-metadata-rewrite contract for cloaked/proxied links. Adapt the lists to your threat model; adapt the proxy page to your meta-tag renderer. Omit CIDR/referrer layers if you only need UA+method fidelity.
