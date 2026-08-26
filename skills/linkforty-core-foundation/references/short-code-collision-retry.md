<!-- capsule-v2 -->
# Short-code collision retry loop — check-then-insert with bounded attempts, custom codes honored

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How are random short codes made unique under concurrency, and where does this pattern knowingly stop being airtight?

## POST /api/links create + duplicate paths
**Path/Symbol:** `src/routes/links.ts` create (:161-183), duplicate (:336-355); generator `src/lib/utils.ts:generateShortCode` (:11-13) via nanoid; template slug twin in `src/routes/templates.ts:132-152`.
**Signature:** `let shortCode = data.customCode || generateShortCode(); ... while (attempts < 10) { SELECT id FROM links WHERE short_code=$1; if none break; shortCode = generateShortCode(); attempts++ } if (attempts >= 10) throw new Error('Unable to generate unique short code')`.
**Data Shape:** Custom codes bypass generation but STILL pass through the uniqueness check loop (a taken custom code silently regenerates a random one); DB enforces the real guarantee via UNIQUE index `idx_links_short_code`.

### Decisive source
```ts
// links.ts:162-181 — the canonical loop:
let shortCode = data.customCode || generateShortCode();
let attempts = 0;
while (attempts < 10) {
  const existing = await db.query('SELECT id FROM links WHERE short_code = $1', [shortCode]);
  if (existing.rows.length === 0) break;
  shortCode = generateShortCode();
  attempts++;
}
if (attempts >= 10) throw new Error('Unable to generate unique short code');
```

**Flow:** generate → probe → collision ⇒ regenerate up to 10× → hard error surfaces to the API caller rather than an unbounded retry → INSERT relies on the UNIQUE constraint as backstop (a race between two concurrent creates can still 23505 past the check — acceptable because nanoid-8 space makes collisions astronomically rare).
**Invariant:** The check-then-insert window is tolerated BY DESIGN; the UNIQUE index is the actual integrity boundary — a porter who drops the index while keeping the loop ships silent duplicate codes; bound every retry loop.
**Probe:** per-file line counts: `bash -c "grep -cF 'attempts >= 10' src/routes/links.ts"` → 2 (create :180 + duplicate :353); `bash -c "grep -cF 'attempts >= 10' src/routes/templates.ts"` → 1 (:150 slug twin); direct tests `src/lib/utils.test.ts`: describe('generateShortCode') length/uniqueness cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "generateShortCode attempts unique collision", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bounded regenerate-and-probe with a UNIQUE-constraint backstop for human-short identifiers; adapt alphabet/length; do not port the check-then-insert into high-contention identifier minting without upgrading to INSERT-on-conflict.
