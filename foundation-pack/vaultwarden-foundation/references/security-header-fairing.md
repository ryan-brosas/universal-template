<!-- capsule-v2 -->
# Security-header fairing — how do you ship strict CSP for a vault SPA without breaking WebSockets, connectors and store extensions?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** Which headers are conditionally REMOVED, for exactly which routes, and why?

## Conditional header surgery in one response hook
**Path/Symbol:** `src/util.rs:26-206` (`AppHeaders` Fairing `on_response`).
**Data Shape:** baseline set: Permissions-Policy (deny-all list), Referrer-Policy same-origin, X-Content-Type-Options nosniff, X-Robots-Tag noindex, X-XSS-Protection 0 ("Obsolete… unsafe (XS-Leak)"), Cross-Origin-Resource-Policy same-origin, plus route-shaped CSP/X-Frame-Options.

### Decisive source
```rust
// WebSocket upgrade: strip headers that break reverse proxies / CloudFlare handshakes
if req_uri_path.ends_with("notifications/hub") || req_uri_path.ends_with("notifications/anonymous-hub") {
    match (req_headers.get_one("connection"), req_headers.get_one("upgrade")) {
        (Some(c), Some(u)) if c.to_lowercase().contains("upgrade") && u.to_lowercase().contains("websocket") => {
            res.remove_header("X-Frame-Options");
            res.remove_header("X-Content-Type-Options");
            res.remove_header("Permissions-Policy");
            return;
        } (_, _) => (),
    }
}
// Images skip CORP; connector pages drop X-Frame-Options so WebAuthn/Duo popups can iframe them;
// CSP frame-ancestors allowlists the Bitwarden store extensions explicitly:
// chrome-extension://nngceckbapebfimnlniiiahkandclblb (Chrome), jbkfoedolllekgbhcbcoahefnbanhhlh (Edge), moz-extension://*
```

**Flow:** every response passes the fairing → websocket upgrade? early-return after removals → image response OR icon_external route? skip CORP only → connector.html? no X-Frame-Options and a CSP tuned for popup flows → otherwise full CSP with img-src allowances for HIBP/2FA-directory/mail-relay services documented inline.
**Invariants:** (1) Header policy is ROUTE-AWARE at the framework layer, not scattered across handlers — porters must keep the exceptions adjacent to the default set. (2) The comment pins co-maintenance: `admin_diagnostics.js checkSecurityHeaders` re-verifies these headers at runtime; renaming one breaks the diagnostic. (3) X-XSS-Protection 0 is deliberate (the header is harmful in modern browsers).
**Probe:** `grep -c 'remove_header' src/util.rs` → `4`.

## Caching + ETag responders
**Path/Symbol:** `src/util.rs:210-370` (`Cached{long,short,ttl}`, `etag` responder with If-None-Match handling).
**Data Shape:** long = immutable 365d for static assets; short for icons (with must-revalidate); ETag comparisons return 304.
**Probe:** `grep -c 'pub fn long\|pub fn short\|pub fn ttl' src/util.rs` → `3`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "AppHeaders", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt central fairing with documented per-route exceptions; adapt the extension IDs/CSP allowlist to your clients; omit the diagnostics coupling only if you reimplement the check elsewhere.
