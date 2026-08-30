<!-- capsule-v2 -->
# Dynamic-update query builder — camelCase→snake_case key mapping with JSONB stringification split

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do partial-update PATCH/PUT handlers map API field names to SQL columns without an ORM?

## PUT /api/webhooks/:id and PUT /api/links/:id builder
**Path/Symbol:** `src/routes/webhooks.ts:111-180`; `src/routes/links.ts:231-306` (with the JSONB branch :251-263); template twin `src/routes/templates.ts:228-279` (explicit per-field variant).
**Signature:** `const updates: string[] = []; const values: any[] = []; let paramIndex = 1; ... updates.push(\`${dbKey} = $${paramIndex}\`); values.push(value); paramIndex++` then `UPDATE t SET ${updates.join(', ')} WHERE id = $N [AND user_id = $N+1] RETURNING *`.
**Data Shape:** Only `value !== undefined` fields become SET arms; empty updates throw ('No fields to update' / 'No updates provided') BEFORE touching SQL; JSONB columns (utmParameters/targetingRules/deepLinkParameters/headers/settings) are detected by name and pushed as `JSON.stringify(value)`; `updated_at = NOW()` appended unconditionally.

### Decisive source
```ts
// links.ts:251-262 — the two-arm value transform:
Object.entries(data).forEach(([key, value]) => {
  if (value !== undefined) {
    if (key === 'utmParameters' || key === 'targetingRules' || key === 'deepLinkParameters') {
      updates.push(`${key.replace(/([A-Z])/g, '_$1').toLowerCase()} = $${paramIndex}`);
      values.push(JSON.stringify(value));          // JSONB arm
    } else {
      const dbKey = key.replace(/([A-Z])/g, '_$1').toLowerCase();
      updates.push(`${dbKey} = $${paramIndex}`);   // scalar arm
      values.push(value);
    }
    paramIndex++;
  }
});
```

**Flow:** zod schema validates + restricts writable fields first (updateLinkSchema = createLinkSchema.partial().extend({isActive}).omit({userId}) — ownership is NOT client-writable) → optional pre-read for post-write invalidation needs (links) → build → execute → zero rows ⇒ 'not found' error.
**Invariant:** camelCase→snake_case via regex must run on TRUSTED schema keys only — never interpolate raw user keys into SQL text; userId scoping appends a parameterized AND-clause when present; JSONB columns need explicit stringify or pg sends objects that fail.
**Probe:** `bash -c "grep -cF 'toLowerCase()' src/routes/links.ts"` → 2 (:254 JSONB arm + :257 scalar arm; the raw `_$1` pattern is NOT probe-safe — bash expands `$1` inside double quotes, so anchor on the method call instead); webhooks.ts uses an explicit per-field list (its own canonical variant); direct tests: none target these handlers directly; recorded honest caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "updates values paramIndex dynamic update", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the allowlist-schema-then-dynamic-SQL pattern with the empty-update guard; adapt naming convention; prefer webhooks-style explicit field lists when your column set is small and stable — reach for the regex mapper only with schema-owned keys.
