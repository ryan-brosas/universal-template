<!-- capsule-v2 -->
# Template default-fallback settings — reusable link presets with exclusive is_default per owner scope

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do org-level defaults flow into individual links, and how is "the default template" kept exclusive?

## templateRoutes + settings consumption chain
**Path/Symbol:** `src/routes/templates.ts:templateRoutes` (:65-368); schema with `defaultAttributionWindowHours` 1-2160 (:12-35); consumption at redirect.ts :544-551 (URLs) — NOTE: attribution-window and UTM/targeting defaults are stored but NOT read by the redirect path this pin.
**Signature:** Template settings `{ defaultIosUrl?, defaultAndroidUrl?, defaultWebFallbackUrl?, defaultAttributionWindowHours?, utmParameters?, targetingRules?, expiresAfterDays? }`; slugs auto-generated via nanoid customAlphabet lowercase+digits, 8 chars.
**Data Shape:** links.template_id FK ON DELETE SET NULL; delete guard refuses when any link references the template (:290-297) — so SET NULL never actually fires through the API path.

### Decisive source
```ts
// templates.ts:154-166 — exclusive-default maintenance at CREATE:
if (data.isDefault) {
  if (data.userId) {
    await db.query('UPDATE link_templates SET is_default = false WHERE user_id = $1', [data.userId]);
  } else {
    await db.query('UPDATE link_templates SET is_default = false WHERE user_id IS NULL');
  }
}
// UPDATE twin excludes self: '... WHERE user_id = $1 AND id != $2' (:217)
```

**Flow:** create/update/set-default all maintain one-default-per-scope by clearing others first (NULL-user scope handled explicitly via `user_id IS NULL`) → resolution-time the redirect LEFT JOINs template+organization rows and reads `settings` JSONB as the MIDDLE tier of the URL fallback chain → delete blocked while referenced.
**Invariant:** The two unset arms must stay scope-exact (owner-scoped vs global-NULL): clearing across scopes would steal another tenant's default; delete-guard precedes delete so referential integrity never depends on the FK action alone.
**Probe:** `bash -c "grep -cF 'SET is_default = false' src/routes/templates.ts"` → 6 (create ×2, update ×2, set-default ×2); direct tests: none target templates.ts — recorded honest caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "link_templates is_default settings slug", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt preset-objects-as-middle-tier defaults with scope-exact exclusivity maintenance; adapt setting names; omit expiresAfterDays-style fields your resolver doesn't read — but keep the guard-before-delete posture for any FK-referenced preset.
