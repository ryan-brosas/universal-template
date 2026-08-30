<!-- capsule-v2 -->
# Generated-manifest drift — how do you keep a GENERATED ledger honest without false drift from informational fields?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A manifest/ledger file is regenerated from source-of-truth state (catalog + disk) and committed so reviewers can diff it. But it carries an informational `generated` date that changes daily — a naive byte or JSON comparison false-drifts on every fresh clone. How do you make `--check` deterministic while still catching every REAL drift (membership, removals, notes)?

## Date-excluded semantic comparison over a deterministically derived retained set
**Path/Symbol:** `scripts/sync-skill-manifest.mjs` (whole, 107L) — retained derivation :52-62, REMOVED ledger :64-81, document assembly :83-89, date-excluded compare :91-100, check/write split :101-107. Independent re-derivation consumer: `scripts/validate-skill-packs.mjs` :233-250 (manifest parity block). Catalog algebra: references/skill-pack-catalog-algebra.md.
**Signature:** `node scripts/sync-skill-manifest.mjs [--check]` (no root arg — always the repo root; `[skip]` exit 0 when `.pi/skills` absent; default mode WRITES, `--check` never writes).
**Data Shape:** manifest = `{generated: 'YYYY-MM-DD' (informational), note: string (structural prose), removed: [{name, reason}] (preserved VERBATIM from a hardcoded ledger — history is not regenerable), retained: [{name, status:'retained', pack: 'core'|packId|undefined, modelVisible: boolean}]}`. Retained is derived from DISK (findSkillFiles minus routers), sorted by `name.localeCompare`, pack resolved as `core.has(name) ? 'core' : packOf.get(name)` where packOf comes from packs.json.

### Decisive source
```js
// The generated date is informational and changes daily, so a committed
// manifest legitimately carries an earlier date on a fresh clone. Compare
// everything except the date: --check stays deterministic and still catches
// real drift in the note, removed ledger, or retained entries.
const sameContent = (a, b) => {
  try {
    const pa = JSON.parse(a)
    const pb = JSON.parse(b)
    delete pa.generated
    delete pb.generated
    return JSON.stringify(pa) === JSON.stringify(pb)
  } catch {
    return false
  }
}
if (current && sameContent(current, text)) { console.log('[ok] manifest is current'); process.exit(0) }
if (check) { console.error('[fail] manifest drift: run node scripts/sync-skill-manifest.mjs to regenerate'); process.exit(1) }
writeFileSync(manifestPath, text)
```

**Flow:** derive retained deterministically (disk discovery → exclude routers by directory shape → map to {name, pack, modelVisible} → localeCompare sort) → assemble the document with the verbatim removed ledger and today's date → if a committed manifest exists and equals the new one EXCEPT for `generated`, report current and exit 0 → otherwise, in `--check` mode fail without writing (CI gate), in default mode write and report regenerated. The validator (validate-skill-packs) independently re-derives the SAME retained set from catalog+disk and JSON-compares it against `manifest.retained`, additionally requiring `manifest.generated` to be present — two independent derivations must agree, so neither the generator nor the validator can silently change the entry shape.
**Invariant:** `--check` is deterministic across time and clones: the only field allowed to differ between a committed manifest and a fresh derivation is the informational date; any difference in note, removed, or retained is drift and fails. The removed ledger is data, not computation — historical removal reasons are preserved verbatim forever (regeneration never loses history). Sort order is part of the contract (localeCompare), so derivation is byte-stable.
**Probe:** LIVE this pass: `node scripts/sync-skill-manifest.mjs --check` on this checkout → `[skip] .pi/skills is not in this checkout; manifest sync applies to the development tree`, exit 0. No direct unit test exists; the date-exclusion semantics are pinned by source comment + logic only. Its chain position (second gate, right after validate-skill-packs) in scripts/check.mjs means CI runs the non-writing form.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "sync-skill-manifest generated retained removed manifest drift", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-part pattern: (1) derive the regenerable section deterministically (sorted, shape-stable entries); (2) keep the non-regenerable history section as a verbatim preserved ledger inside the same document; (3) compare with the informational timestamp EXCLUDED (parse both sides, delete the key, stringify-compare) so committed artifacts age gracefully while real drift still fails. Keep the check/write mode split (`--check` for CI, bare for local repair). Adapt which fields are informational (any wall-clock or nonce field) and the sort key to your ledger. Omit the specific removed entries — they are this repo's migration history. Caveat: the validator's independent re-derivation duplicates the generator's logic; if the entry shape ever changes, BOTH sides must change together (no shared module at this pin).
