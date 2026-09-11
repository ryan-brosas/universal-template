<!-- capsule-v2 -->
# Work-management contract gate — how do you pin a workflow's local-by-default contract and durable-record layout in a pure-read gate?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A repo's workflow prompts (create/plan/ship/verify) accumulate legacy vocabulary, external-service coupling, and durable-record paths that drift from the intended contract. How do you pin "local by default, durable records in one place, optional external linkage" as a structural gate that survives prose edits?

## Ordered contract sections over prompts, work dir, templates, and GitHub templates
**Path/Symbol:** `scripts/validate-work-management.mjs` (whole, 160L) — skip gate :10-13, artifacts scan :22-45, bead scan :82-98, prompt needle table :101-115, normalize-before-regex :126, durable-under-artifacts regex :129, active-pointer grammar :151-157.
**Signature:** `node scripts/validate-work-management.mjs [root]` (default root = repo root via `fileURLToPath(new URL('..', import.meta.url))`).
**Data Shape:** per-check output is a `[ok]`/`[fail]` console line with a `failures` counter driving the final exit (`work-management contract: ok|FAIL`, exit 0/1). The prompt needle table maps prompt filename → array of literal needles, with one MAGIC needle `'no-durable-under-artifacts'` handled by regex instead of `includes`.

### Decisive source
```js
// :126 normalize the active-pointer indirection BEFORE the durable-write regex
const normalized = text.replaceAll('$(cat .pi/work/.active)', 'ACTIVE')
for (const check of checks) {
  if (check === 'no-durable-under-artifacts') {
    if (/\.pi\/artifacts\/[^\s`]*\/(spec|plan|tasks|research|design|verification)\.md/.test(normalized))
      fail(name + ' writes a durable record under artifacts')
    else ok(name + ' writes no durable record under artifacts')
  } else if (text.includes(check)) ok(name + ' uses ' + check)
  else fail(name + ' missing ' + check)
}
```

## Flow
1. Skip gate: `.pi` absent → `[skip]` exit 0 (dev tree vs published checkout vs CI all run the same command).
2. Section 1 — artifacts eradication: every workflow prompt must exist and must NOT reference `.pi/artifacts`; `.pi/work/.active` and `.pi/MEMORY.md` are the local-state contracts.
3. Section 1b — create.md local-by-default pinned NEGATIVELY: must NOT contain `gh issue create` (never creates GitHub issues) and must NOT contain "Resolve the GitHub issue before creating any local record" (local records never block on GitHub); pinned POSITIVELY: optional `--issue <number>` linkage and `gh issue view` verification, plus slug-based local identity.
4. Section 2 — bead-metadata eradication: case-insensitive `/bead/i` scan over EVERY `.md` under `.pi/templates` AND `.pi/prompts` (not a listed subset), so legacy vocabulary cannot return through an unlisted file or a "Bead ID:" variant.
5. Section 3 — prompt path ownership: the needle table pins durable writes to `.pi/work/$(cat .pi/work/.active)/…` (plan/ship/verify) with `progress.md`/`verification.md`/`verify.log` artifacts; the indirection is normalized to `ACTIVE` before the durable-under-artifacts regex so write-side indirection is detectable while read guards (`.pi/work/.../spec.md`) stay clean.
6. Section 4 — GitHub issue forms (feature/bug/research/config.yml) + PR template must exist.
7. Section 5 — active pointer: only when `.pi/work/.active` exists, its content must match `^[a-z0-9][a-z0-9-]*$` or `^[0-9]+-[a-z0-9-]+$` (`<slug>` or `<issue>-<slug>`) and resolve to a real `.pi/work/<id>` dir.

## Invariant
- The gate is pure-read: it never mutates the tree; failures accumulate, the exit code is the only side effect.
- Local-by-default is enforced by ABSENCE needles (`gh issue create` must not appear), optional coupling by PRESENCE needles — absence checks rot-proof the negative contract.
- Legacy vocabulary is scanned case-insensitively over every file in the guarded dirs, never a curated list.
- **Deepest-path gate defect (live):** the skip gate checks only `.pi` (:10) but the bead scan needs `.pi/templates` (:83) — on a checkout with a partial gitignored `.pi/` (fabric/ + work/ only) it prints graceful `[fail]` lines for missing prompts, then CRASHES with unhandled `ENOENT` at `readdirSync(.pi/templates)` :83, exit 1. Gate granularity must match the deepest touched path, not the shallowest.

## Probe
No direct unit test exists for this script at this pin (recorded caveat). Executed live probe:
```
node scripts/validate-work-management.mjs
# → [fail] missing .pi/prompts/create.md … [fail] missing .pi/templates/issue.md
# → Error: ENOENT … scandir '…/.pi/templates' at validate-work-management.mjs:83 → exit 1
```
The crash line :83 (bead scan) is the exact deepest-path granularity defect; pass-7's ":50" attribution belonged to release-hygiene, not this script.

## Retrieve
`search_graph(project="pi-acp", q="validate-work-management active pointer bead artifacts", mode="ids")` — revalidate `validate-work-management` symbol presence at the current pin (graph unavailable passes 5–8; direct read is the authority).

## Adopt/Adapt/Omit Verdict
**Adapt.** Adopt: normalize-indirection-before-regex for write-vs-read path contracts; negative (absence) pins for "never do X" workflow rules with positive pins for the optional escape hatch; case-insensitive whole-dir legacy scans; active-pointer grammar validated only when state exists. Adapt: gate on the DEEPEST path your checks touch (this script's `.pi`-only gate is the counterexample); report `[fail]` lines before crashing instead of unhandled ENOENT. Omit: the repo-specific GitHub issue-form inventory and bead history.
