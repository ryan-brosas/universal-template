<!-- capsule-v2 -->
# Foreign-schema parser whitelist — how do you read another tool's private config files (codex cache, pi models.json, factory settings) without trusting them, including keeping secrets out of your own data model?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** When your catalog command must ingest private files owned by *other* CLIs — schemas you do not control and that may contain credentials — what parser contract keeps your data model clean, secret-free, and total (never throwing)?

## Connected graph-selected seam
**Path/Symbol:** `src/agent/model-catalog.ts:parseCodexCatalog` (:230–245), `parseAgyModels` (:248–261), `parseDroidCustomModels` (:268–281), `parsePiCatalog` (:287–307). File header contract (:15–18): "All parsers are defensive: they whitelist fields, skip malformed records, and degrade to a labeled unavailable/partial section instead of throwing. External files … are private foreign schemas — never trusted."
**Signature:** all four are total: `(value: unknown) => CatalogModel[]` (agy takes `stdout: string`). No exceptions, no partial throws.
**Data Shape:** input is hostile `unknown` (or raw stdout); output rows carry ONLY whitelisted fields: `id`, optional `displayName`, a provenance `source` tag, and at most one marker (`custom` for droid, `configured` for pi). Nothing else crosses the boundary.

### Decisive source
```ts
/**
 * Extract custom models from ~/.factory/settings.json. Whitelists ONLY `id`
 * and `displayName`; baseUrl/apiKey/provider never cross the boundary.
 * Normalizes a missing `custom:` prefix. Skips entries without a usable id.
 */
export function parseDroidCustomModels(value: unknown): CatalogModel[] {
  const list = (value as { customModels?: unknown })?.customModels;
  if (!Array.isArray(list)) return [];
  const out: CatalogModel[] = [];
  for (const entry of list) {
    const rec = entry as Record<string, unknown>;
    const rawId = rec?.id;
    if (typeof rawId !== 'string' || rawId.length === 0) continue;
    const id = rawId.startsWith('custom:') ? rawId : `custom:${rawId}`;
    const displayName = typeof rec.displayName === 'string' ? rec.displayName : undefined;
    out.push({ id, displayName, source: 'droid-settings', custom: true });
  }
  return out;
}
// parsePiCatalog builds canonical ids at the boundary:
out.push({
  id: `pi/${provider}/${id}`,
  displayName: typeof name === 'string' ? name : undefined,
  source: 'pi-config',
  configured: true,
});
// parseCodexCatalog filters + orders: visibility gate then stable priority sort:
if (rec.visibility !== 'list') return;
const priority = typeof rec.priority === 'number' ? rec.priority : Number.MAX_SAFE_INTEGER;
rows.sort((a, b) => a.priority - b.priority || a.index - b.index);
```

**Flow:** type-guard the top-level shape (`Array.isArray` / `typeof === 'object'`) → iterate entries → per-entry `typeof` whitelist of each field you keep → skip entries lacking a usable id (never guess) → normalize ids at the boundary (`custom:` prefix added if absent; `pi/<provider>/<id>` composed from the provider map key) → tag provenance per row. For text output (agy): trim lines, drop empties, drop known noise lines (`/^fetching/i`), split on first tab, tolerate missing display name.
**Invariant:** the parsers are total over all inputs — `undefined`, wrong shapes, empty arrays all yield `[]`; only whitelisted fields survive, so `baseUrl`/`apiKey`/`provider` from a foreign settings file can never enter your data model even when present in the source; unknown/malformed entries are skipped individually, not fatal to the batch; codex keeps only `visibility === 'list'` rows and orders by priority ascending with original-index tiebreak (missing priority sorts last via `Number.MAX_SAFE_INTEGER`); id normalization happens exactly once, at parse time, so downstream code sees canonical ids only.
**Probe:** `tests/agent/model-catalog.test.ts` (executed green at pin, part of 29 pass / 0 fail) — the droid describe block plants `apiKey: 'SECRET'`, `baseUrl: 'http://x'`, `provider: 'generic'` in fixtures and asserts `JSON.stringify(row)` contains none of them, plus prefix normalization (`NoPrefix-2` → `custom:NoPrefix-2`) and no-id skip; codex block pins visibility filter + priority sort + `[]` on `{}`, `{models:'nope'}`; agy block pins tab parsing, "Fetching…" noise skip, bare-slug tolerance; pi block pins canonical `pi/<provider>/<id>` composition + `configured` marker + `[]` on missing providers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "parseDroidCustomModels parsePiCatalog parseCodexCatalog parseAgyModels whitelist", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the contract: total functions over `unknown`, per-field `typeof` whitelisting, skip-don't-fail on individual entries, boundary-time id normalization, per-row provenance tags, and — where the foreign file may hold credentials — an explicit whitelist so secrets are excluded by construction rather than by remembering to delete them. Adapt the field names, noise-line regexes, and canonical-id grammar to your host's foreign tools. Omit nothing behavioral; add a test that plants a fake secret in the fixture and asserts it cannot appear in any output row — that assertion is what makes the whitelist real instead of aspirational.
