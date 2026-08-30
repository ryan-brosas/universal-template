<!-- capsule-v2 -->
# Footer href URL-parse scheme gate — how do you validate an admin-supplied link href so `javascript:` can never survive into an anchor?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** Where is the scheme allowlist enforced, and why parse instead of pattern-match?

## isValidFooterLinkHref — parse-don't-match, absolute http(s) only
**Path/Symbol:** `apps/web/src/features/instance-settings/schema.ts:isValidFooterLinkHref` (lines 58–71); wired via `footerLinkSchema` refine (lines 73–84); bounds `FOOTER_LINK_MAX_COUNT=5` / `MAX_LABEL_LENGTH=40` / `MAX_HREF_LENGTH=2048` (lines 40–42).
**Signature:** `isValidFooterLinkHref(href: string) → boolean`.
**Data Shape:** trim first; empty/whitespace → false; `new URL(value)` throw → false; else `protocol === "http:" || protocol === "https:"`.

### Decisive source
```ts
/**
 * Admin-typed hrefs are rendered into an anchor, so the scheme is the whole
 * security question: `javascript:` must never survive validation. Parsing with
 * `URL` rather than pattern matching avoids the usual bypasses — browsers strip
 * control characters and tolerate case and whitespace variants, so `jAvA\tscript:`
 * is one scheme to a browser and several to a regex.
 */
export function isValidFooterLinkHref(href: string) {
  const value = href.trim();
  if (!value) return false;
  try {
    const { protocol } = new URL(value);
    return protocol === "http:" || protocol === "https:";
  } catch {
    return false;
  }
}
```

**Flow:** admin submits links → `footerLinkSchema.refine(isValidFooterLinkHref)` runs inside the safe-action `inputSchema` (see `safe-action-procedure-ladder` for the tier; this action rides `adminActionClient`) → only absolute http(s) survives → the same predicate re-runs at read time (see `footer-links-drop-on-read-roundtrip`). Relative paths were considered and REJECTED: these links must also resolve from emails, where there is no base to resolve against.
**Invariant:** the browser's URL parser is the single normalization authority — case (`JavaScript:`), embedded control chars (`java\tscript:`), leading whitespace, `data:`, `vbscript:`, `file:`, `mailto:`, and scheme-relative `//evil.example.com` all collapse to false because they fail the two-protocol allowlist after real parsing. A denylist or regex here is the wrong shape: it must enumerate everything the browser accepts; the allowlist only enumerates what you accept.
**Probe:** direct test `apps/web/src/features/instance-settings/schema.test.ts:4–54` — pins `java\tscript:alert(1)` → false (:22–25), `//evil.example.com` → false (:36–38), bare hostname ambiguity → false (:46–48). Runner caveat: vitest unavailable in checkout (no node_modules) — assertions read directly at pin.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "isValidFooterLinkHref footerLinkSchema", limit: 10 });
```

## Verdict
Adopt the parse-then-allowlist shape verbatim for any admin/user string rendered as a link target; adapt the protocol set to your context (e.g. add `mailto:` only if you render mail anchors); omit the email-resolution rationale if your links never leave the app — but re-run the relative-path decision consciously, not silently. Note the schema's error message is deliberately un-localized (server contract validates without a request locale); the UI layers its own translated message over the same predicate.
