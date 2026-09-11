<!-- capsule-v2 -->
# Vary: Accept on both variants — how do you keep content-negotiated markdown/HTML responses cache-safe before any shared cache exists?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** One URL serves two representations negotiated on Accept; only the markdown variant declared Vary — why must BOTH, and how is it added idempotently?

## AddVaryAcceptHeader middleware appended after ProvideMarkdownResponse
**Path/Symbol:** `app/Http/Middleware/AddVaryAcceptHeader.php` :21 `handle(Request, Closure)`.
**Signature:** standard terminable-less middleware; `setVary('Accept', replace: false)` appends without clobbering existing Vary entries.
**Data Shape:** Registered in every content-negotiated group: `routes/web.php` :54, `config/ink.php` :42 (blog), `packages/Documentation/routes/web.php` :11/:18 (developers + help).

### Decisive source
```php
if ($response instanceof Response && ! in_array('Accept', $response->getVary(), true)) {
    $response->setVary('Accept', replace: false);
}
```
(:25-27). Class docblock states the latent-bug framing: "ProvideMarkdownResponse sets `Vary: Accept` only on the markdown variant; the HTML variant of the same URL leaves without it. That is latent while responses are `Cache-Control: private`, but the moment a shared cache (CDN) keys on the URL alone it will replay one variant to clients that asked for the other."

**Flow:** request → ProvideMarkdownResponse picks variant by Accept → AddVaryAcceptHeader runs AFTER it in the group → HTML response gets the missing declaration; markdown's existing one is detected via getVary() and left alone (no duplicate).
**Invariant:** Cache correctness requires ALL variants of a URL to declare the SAME Vary set; fixing only one variant leaves the other poisoning the cache. The membership check makes re-entry (multiple middleware layers) harmless.
**Probe:** coverage caveat: no direct unit test for this middleware at this pin — pinned by middleware source + registration-site grep across three groups (verified this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "AddVaryAcceptHeader ProvideMarkdownResponse setVary", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt symmetric-Vary-on-every-variant with append-if-missing semantics whenever one route serves multiple negotiated representations; adapt to your middleware stack; omit nothing — the pattern is three lines and fully portable. Honest caveat: source-pinned, no dedicated test.
