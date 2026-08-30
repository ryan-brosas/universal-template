<!-- capsule-v2 -->
# SSRF-fenced rewrite proxy — how do you show a hostile foreign login page inside your local app without tripping CORS or frame-busting?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** the vendored dashboard must probe and render linkedin.com pages same-origin; what header surgery and reinjection keeps that working and safe?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/server.ts` inline `/li-proxy` branch inside `handle` (lines 391-440); ownership anchor `isLoopbackOrigin`/dispatcher confirmed by trace `createAppServer -> handle`.
**Signature:** `GET|HEAD /li-proxy?url=<encoded absolute URL>`.
**Data Shape:** query param url required else 400 JSON; target hostname must end `linkedin.com`/`licdn.com` else 403; forwards User-Agent, Accept-Language, Cookie; upstream failure -> 502 JSON.

### Decisive source
```ts
if (url.pathname === "/li-proxy" && (method === "GET" || method === "HEAD")) {
  const targetUrl = url.searchParams.get("url");
  if (!targetUrl) { json(res, 400, { error: "missing url param" }); return; }
  const target = new URL(targetUrl);
  if (!target.hostname.endsWith("linkedin.com") && !target.hostname.endsWith("licdn.com")) {
    json(res, 403, { error: "only LinkedIn domains allowed" }); return; }
  const proxyReq = await fetch(targetUrl, { headers: { /* UA + Accept-Language + Cookie passthrough */ }, redirect: "follow" });
  const headers = new Headers(proxyReq.headers);
  headers.delete("x-frame-options"); headers.delete("content-security-policy");
  headers.delete("content-security-policy-report-only"); headers.delete("x-content-type-options");
  headers.delete("content-encoding"); headers.delete("content-length"); headers.delete("transfer-encoding");
  // HTML only: inject <base href=target> + capture-phase click listener rewriting
  // outbound linkedin/licdn hrefs back to /li-proxy?url=<encoded>
}
```
**Flow:** method gate accepts HEAD (the dashboard probes reachability with `fetch('https://www.linkedin.com/', {method:'HEAD'})`) -> missing-url 400 -> host fence 403 -> fetch with cookie passthrough -> strip frame/CSP/length/encoding headers -> for text/html inject `<base>` + link-capture script -> pass non-HTML bodies untouched.
**Invariant:** suffix-host fence blocks open-proxy/SSRF reuse; stripped framing headers are exactly the ones that break in-app rendering; asset URLs keep working because `<base>` resolves relative paths against the ORIGINAL page.
**Probe:** `packages/app/test/li-proxy.test.ts` — "answers HEAD /li-proxy" pins missing-url=400 over HEAD (regression: GET-only routing returned 404/static); "rejects non-LinkedIn targets for HEAD" pins evil.example=403.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ultireaaach", query: "li-proxy", limit: 5 });
// observed: hits land in the vendored minified bundle (front/build) — the handler itself is an
// inline branch of server.handle; ownership proven by trace_path createAppServer -> handle (depth 1).
await mcp.codebase_memory.trace_path({ project: "ultireaaach", function_name: "ultireaaach.packages.app.src.server.createAppServer", direction: "outbound", depth: 1 });
// observed callees_total 2: packages.app.src.server.handle (+ bundle noise)
```

## Verdict
Adopt the allow-list fence + strip list + base-tag/click-capture reinjection trio whenever a local app must render a third-party page. Adapt the domain suffixes and injected script to your target site. Omit LinkedIn-specific cookie forwarding when your source page needs no session.
