<!-- capsule-v2 -->
# Social-scraper OG preview hook — bots get meta tags instead of redirects via a preHandler short-circuit

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do link previews render on social platforms when those platforms' crawlers follow short links?

## isSocialScraper + generatePreviewHTML + global preHandler hook
**Path/Symbol:** `src/routes/preview.ts:isSocialScraper` (:8-26), `generatePreviewHTML` (:31-140), `previewRoutes` preHandler hook (:202-251).
**Signature:** `function isSocialScraper(userAgent: string): boolean`; hook registered via `fastify.addHook('preHandler', ...)` BEFORE the parametric redirect route.
**Data Shape:** Scraper UA patterns: facebookexternalhit/Facebot/Twitterbot/LinkedInBot/Slackbot/Discordbot/TelegramBot/WhatsApp/PinterestBot/SkypeUriPreview/Googlebot/bingbot/ia_archiver; preview HTML carries og:* + twitter:* tags and NO meta-refresh for bots (autoRedirect=false).

### Decisive source
```ts
// preview.ts:203-211 — route-class guard so API/asset paths skip the hook:
if (
  path.startsWith('/api/') ||
  path.endsWith('/preview') ||
  path === '/' ||
  path.includes('.')
) {
  return; // Skip this hook
}
// :237-243 — short-circuit: send HTML and STOP before the redirect handler:
reply.header('Content-Type', 'text/html; charset=utf-8').send(html);
return reply;
```

**Flow:** every non-API/non-preview path passes the hook → scraper UA? → direct SQL lookup (active+unexpired, NOT the Redis cache) → found ⇒ serve static OG HTML without auto-redirect (bots must not bounce) → humans fall through to normal redirect. Human-facing `/:shortCode/preview` route serves the same generator WITH a 2-second meta refresh. Error inside the hook is caught-and-logged, continuing to the normal redirect (fail-open).
**Invariant:** The hook must be registered before `/:shortCode` and must skip dotted paths (static files); bot responses carry no auto-redirect while human previews do; escaping goes through the local escapeHtml for EVERY interpolation including og:image.
**Probe:** `bash -c "grep -cF 'facebookexternalhit' src/routes/preview.ts"` → 1 (:9); direct tests: none target preview.ts — this seam is test-uncovered (recorded honestly); behavior pinned only by source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "isSocialScraper preview og meta tags", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt UA-class-based content negotiation for crawler-vs-human on share endpoints; adapt pattern list to platforms you care about; omit the human preview route if you have no share UI — keep the fail-open catch either way so preview breakage can never take down redirects.
