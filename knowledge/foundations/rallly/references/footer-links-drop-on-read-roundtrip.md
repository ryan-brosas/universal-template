<!-- capsule-v2 -->
# Footer links drop-on-read roundtrip — what happens when the stored footer JSONB was edited outside the app, and why does write and read share ONE schema?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How is a directly-DB-edited footer column kept from injecting an unsafe href or breaking the login page?

## parseFooterLinks — per-entry safeParse, drop invalid, re-slice to cap
**Path/Symbol:** `apps/web/src/features/instance-settings/data.ts:parseFooterLinks` (lines 15–26); consumed at `getInstanceSettings` line 59; the shared schema `apps/web/src/features/instance-settings/schema.ts:footerLinksSchema` (lines 88–90); action input `apps/web/src/app/[locale]/control-panel/settings/actions.ts:updateFooterLinksAction` (lines 24–41).
**Signature:** `parseFooterLinks(value: unknown) → FooterLink[]`.
**Data Shape:** input is whatever the JSONB column holds (`unknown`); output is a bounded array of validated `{label, href}` — never throws.

### Decisive source
```ts
// Stored links are re-validated on read, not just on write: a row edited
// directly in the database must not be able to put an unsafe href into an
// anchor, or turn the footer into a link farm. Invalid entries are dropped
// rather than failing the whole read, so one bad link cannot take down the
// login page.
function parseFooterLinks(value: unknown): FooterLink[] {
  if (!Array.isArray(value)) return [];
  return value
    .flatMap((entry) => {
      const parsed = footerLinkSchema.safeParse(entry);
      return parsed.success ? [parsed.data] : [];
    })
    .slice(0, FOOTER_LINK_MAX_COUNT);
}
```

**Flow:** form submits → action's `inputSchema(footerLinksSchema)` validates at the boundary → `updateInstanceFooterLinks` writes the parsed plain-JSON array into the JSONB column (see `singleton-tag-cache-store`) → every read goes back through the SAME schema per entry: non-array → [], bad entry → dropped alone, over-cap list → sliced to 5. Deployment asymmetry rides the loaders: `loadFooterLinks` returns [] when not self-hosted (legal-disclosure links are deliberately NOT behind the white-label add-on, unlike the rest of branding), while the write action throws `AppError FORBIDDEN` on cloud — read silently-empty, write loudly-rejected.
**Invariant:** validation is not a write-time-only gate. Trust boundaries are read boundaries too: anything that can reach the column without the action (migration, manual SQL, another service) meets the identical predicate. One malformed entry degrades exactly itself — never the page, never the other links. The roundtrip test pins that the parsed payload is plain JSON (survives `JSON.parse(JSON.stringify(...))`) because Prisma writes it straight into JSONB.
**Probe:** direct tests `apps/web/src/features/instance-settings/footer-links-roundtrip.test.ts` (whole, 41L — "accepts the payload the form submits", "rejects a payload the server must never persist") and `apps/web/src/features/instance-settings/schema.test.ts:56–107` (trim normalization, empty label/href rejection, count/length caps). Runner caveat: vitest unavailable in checkout — assertions read directly at pin.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "parseFooterLinks getInstanceSettings footerLinks", limit: 10 });
```

## Verdict
Adopt the one-schema-two-sides pattern (inputSchema at write, per-entry safeParse at read) for any JSONB blob rendered into public pages; adapt the drop-vs-fail choice to your blast radius — dropping is right when the blob decorates a page, failing is right when it IS the page; omit the self-host/cloud asymmetry if you have single deployment. Contrast with `activity-event-prefs-codec`, which replaces the WHOLE record on corruption: there prefs are all-or-nothing booleans; here entries are independent links, so per-entry survival maximizes valid content.
