<!-- capsule-v2 -->
# Embed Iframe Client Plane — how does an iframe carry its credential and notify its parent without leaking the token or posting to the wrong origin?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What is the client-side transport contract (token extraction, parent notification, API base resolution) that completes the server-side embed JWT/allowlist/middleware capsules?

## Fragment-in, postMessage-out, bearer-fetch-through trio
**Path/Symbol:** `packages/dashboard/lib/embed/token.ts:extractEmbedToken` (:10–16); `packages/dashboard/lib/embed/post-message.ts` — `EmbedEvent` union (:15–25), `postEmbed` (:29–38); `packages/dashboard/lib/embed/api.ts` — `getApiBase` (:30–43), `embedFetch` (:45–70), `EmbedFetchError` (:20–28). Consumer wiring: `packages/dashboard/app/embed/page.tsx` (`parentOriginRef` best-effort decode :61–67, load/error/complete/resize posts).
**Signature:** `extractEmbedToken(): string | null`; `postEmbed(parentOrigin: string, event: EmbedEvent): void`; `embedFetch<T>(path, { token, ...init }): Promise<T>`.
**Data Shape:** events all carry `source:"awaithumans"` + discriminated `type`: `loaded{taskId}`, `task.completed{taskId,response,completedAt}`, `task.error{taskId,code,message}`, `resize{height}`. Errors normalize to `{error:{code,message}}` envelope codes, non-JSON bodies degrade to `HTTP_<status>`.

### Decisive source
```ts
// post-message.ts — targetOrigin is the JWT's verified parent_origin CLAIM,
// never "*"; the browser drops mismatched deliveries, which IS the guarantee.
if (!parentOrigin) return;            // empty claim disables notify, never widens it
if (window.parent === window) return; // top-level open: nobody to notify, skip silently
window.parent.postMessage({ source: SOURCE, ...event }, parentOrigin);

// api.ts — bundled mode MUST resolve to "" so fetches are same-origin
// (CSP connect-src 'self'); localhost-vs-127.0.0.1 hardcoding breaks it.
if (process.env.NEXT_PUBLIC_AWAITHUMANS_BUNDLED === "true") return "";
```

**Flow:** parent mints embed JWT → iframe URL carries `?id=<task>#token=<jwt>` → `extractEmbedToken` parses ONLY `location.hash` as URLSearchParams (fragments never hit the server, access logs, or cross-origin Referer) → page decodes payload with UNVERIFIED `atob` to read `parent_origin` for notification only ("signature is verified server-side") → task fetched via `embedFetch` with `Authorization: Bearer <fragment-token>` (never cookies, never a second query string) → lifecycle reported one-way via `postEmbed` (`loaded` on fetch, `task.completed` after POST complete, `task.error` on any failure with the envelope code, `resize` from a ResizeObserver so the parent can size the frame) → reopening a completed task's URL shows the done view instead of the form (:82–85).
**Invariant:** the credential exists in exactly two places — URL fragment and Authorization header; parent notification is fail-DISABLED, not fail-open (empty origin skips, `*` is never constructed); every event is source-tagged so a host page filtering multiple iframes can trust attribution.
**Probe:** no vitest suite exists under `lib/embed/` at this pin (glob census of `packages/dashboard/**/*.test.*` lists seven suites, none covering this trio) — coverage caveat recorded. Deterministic source probes executed: grep `"\*"` in post-message.ts → **0 matches**; grep `postMessage|Authorization|location\.hash` across lib/embed → exactly one `window.parent.postMessage(...)` call (:37), one `Authorization: Bearer` construction (api.ts:54), one `location.hash` read (token.ts:12).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "extractEmbedToken postEmbed embedFetch getApiBase", limit: 8 });
```
Live rank-7/18/19 line-exact (:10–16, :45–70, :30–43); name_pattern sweep returns the five symbols with `postEmbed` in-degree 3 (all in app/embed/page.tsx). Note: `embedFetch` has zero resolved CALLS edges (awaited inside an async IIFE) — consumer flow confirmed by direct source read instead.

## Verdict
Adopt fragment-transport + claim-keyed targetOrigin + bearer-only same-origin fetch as ONE unit — splitting them reopens whichever channel you drop. Adapt the event vocabulary and resize mechanics to your host contract. Omit the bundled-mode env branch only if your dashboard is never co-served with the API (then pin the absolute base instead). Direct-test gap acknowledged: port alongside a jsdom suite for extract/postEmbed guards.
