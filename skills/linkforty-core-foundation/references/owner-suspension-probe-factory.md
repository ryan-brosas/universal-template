<!-- capsule-v2 -->
# Owner-suspension SELECT probe factory — memoised in-flight schema probe shared by every link-resolving path

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do you gate behavior on an optional DB column owned by another deployment without failing every request when it is missing?

## createOwnerSuspensionSelect — per-registration promise memoisation returning a SQL fragment
**Path/Symbol:** `src/lib/link-safety.ts:createOwnerSuspensionSelect` (:176-197); instantiated once per route registration at `src/routes/redirect.ts:181-185` AND `src/routes/sdk.ts:453-457`.
**Signature:** `function createOwnerSuspensionSelect(deps: { query: (sql: string) => Promise<{ rows: unknown[] }>; onSupported?: () => void }): () => Promise<string>` — resolves to `', o.suspended_at AS owner_suspended_at'` or `''`.
**Data Shape:** Factory closes over ONE memoised `Promise<string>` (the in-flight promise itself is stored, not just its result, so N concurrent cold requests issue one probe); failure resolves to `''` ("unsupported") via `.catch(() => '')`, never rejects.

### Decisive source
```ts
// link-safety.ts:180-196
let probe: Promise<string> | null = null;
return () => {
  if (!probe) {
    probe = deps.query(
      `SELECT 1 FROM information_schema.columns
       WHERE table_name = 'organizations' AND column_name = 'suspended_at'`
    ).then((r) => {
      const supported = r.rows.length > 0;
      if (supported) deps.onSupported?.();
      return supported ? ', o.suspended_at AS owner_suspended_at' : '';
    }).catch(() => '');
  }
  return probe;
};
```

**Flow:** registration creates its own instance (module-level state would share one answer across every `createServer()` in the process and forced a test-only reset export onto the public API — recorded in redirect.ts :169-172 comment) → first resolution request triggers the information_schema probe → fragment spliced into BOTH redirect and resolve SELECTs → result cached with the row for TTL 300s.
**Invariant:** Every path that writes Redis key `link:<code>` (or `link:<template>:<code>`) must select the SAME columns: whichever path populates the key decides what the OTHER path sees. Omitting `owner_suspended_at` made the redirect read `undefined` → treated as unrestricted → restricted owners' links resolved publicly for a full TTL (sdk.ts :433-451 documents this incident). Omitting `template_settings`/`org_settings` silently breaks the URL fallback chain. A probe error can never take a resolution path down.
**Probe:** `bash -c "grep -cF 'information_schema.columns' src/lib/link-safety.ts"` → 1; direct tests `src/routes/sdk-cache-bypass.test.ts` describe('owner restriction cannot be bypassed through the SDK cache') — 4 cases incl. cross-path cache priming.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "createOwnerSuspensionSelect suspended_at probe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dependency-injected probe factory pattern (per-registration lifetime, memoised in-flight promise, fail-open-to-empty SQL fragment) for any optional-schema feature gate; adapt the probed table/column to yours; omit the specific org-suspension semantics if you have no multi-owner restriction concept.
