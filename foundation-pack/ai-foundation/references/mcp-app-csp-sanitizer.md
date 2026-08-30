<!-- capsule-v2 -->
# MCP App CSP sanitizer — how do untrusted server CSP domains become a safe Content-Security-Policy?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Why canonicalize each CSP source through URL parsing instead of denylisting bad characters on the raw string?

## Canonicalize-then-allowlist source filter
**Path/Symbol:** `packages/react/src/mcp-apps/sandbox.ts` — `sanitizeCSPSources` (:11–44), `ALLOWED_CSP_SCHEMES = {'https:','wss:'}` (:9), `getMCPAppCSP` (:71–95).
**Signature:** `sanitizeCSPSources(sources?: string[]): string[]`; `getMCPAppCSP(csp?: MCPAppResourceCSP): string | undefined`.
**Data Shape:** non-string entries skipped; parse-failures, non-https/wss schemes, empty hosts, and bare `*` hosts are all DROPPED (never rewritten).

### Decisive source
```ts
const url = new URL(source);            // percent-encoding decoded here
if (!ALLOWED_CSP_SCHEMES.has(url.protocol) ||
    url.host.length === 0 || url.host === '*') continue;
origin = url.origin;                    // re-emit the DECODED origin only
...
if (/["'`\s;,]/.test(origin)) continue; // separator/quote check AFTER decode
```

**Flow:** `getMCPAppCSP` builds a fixed 9-directive policy — `default-src 'none'`, `base-uri 'none'`, `form-action 'none'`, `script-src 'unsafe-inline'`, `style-src 'unsafe-inline'`, then `connect-src` (+`'self'`), `img-src` (+`data:`), `font-src` (REUSES the img list by design), `frame-src` — each domain list passed through the sanitizer first → joined with `'; '` for the sandbox proxy to apply to the inner app document.
**Invariant:** The comment IS the threat model: an encoding like `%3B` slips past raw-string denylists, so values must be parsed as absolute URLs (decoding percent-escapes) and re-checked post-decode — otherwise a decoded `;`, `,`, quote, or whitespace splits or breaks out of the directive. A scheme-only `https:` or host `*` would match every origin and defeat the whole allowlist. `script-src 'unsafe-inline'` is deliberate: apps ship inline HTML/scripts and rely on connect/frame restrictions instead.
**Probe:** deterministic: `grep -n "ALLOWED_CSP_SCHEMES.has" packages/react/src/mcp-apps/sandbox.ts` → `24:`; `grep -n "url.host === '\*'" packages/react/src/mcp-apps/sandbox.ts` → `26:`; `grep -c unsafe-inline packages/react/src/mcp-apps/sandbox.ts` → `2`; `grep -n font-src packages/react/src/mcp-apps/sandbox.ts` → `92:`. Direct tests: `sandbox.test.ts:56` encoded separators dropped (`%3B`), `:70` match-all wildcards + quotes dropped, `:88` non-https/wss schemes dropped.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "sanitizeCSPSources CSP sources", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 sandbox.sanitizeCSPSources :11-44
```

## Verdict
Adopt parse-decode-recheck canonicalization and the fixed lockdown directive set verbatim; adapt the directive list to which embed surfaces you support; omit nothing — raw-string filtering is the vulnerability this module exists to prevent.
