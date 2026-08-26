# Foundations Workflow — Wiring & Verification

## Wiring

**Rewrites with unchanged membership:** leave `packs.json`, the router, and the manifest untouched; update only the leaf `SKILL.md`, its references, and the durable work record.

### New membership
1. Add the member and trigger-first description to `.pi/skills/packs.json`.
2. Add the matching router line to `.pi/skills/pack-foundations/SKILL.md`.
3. Update `.pi/skills/manifest.json` to match the on-disk skill and `packs.json` membership.
4. Update `README.md` counts only when membership changes.

Check JSON syntax, exact membership parity, router wording, and manifest entries directly before closing. Record the inspected paths and outcome in the work record.

## Evidence gates

For every rewritten foundation:
1. Confirm the live graph project's root, branch, commit, mode, counts, freshness, and coverage caveats.
2. For each capsule, trace its symbol, read decisive source and its named direct test, and check coverage for every cited path.
3. Confirm each loader entry and Capsule map reference resolves to exactly one existing `capsule-v2` file.
4. Review the diff for accidental catalog or unrelated-file changes.
5. Record the exact commands/tool calls and results in the durable work record; a blocked test runner is a caveat, never a pass.

## Common failures → fixes

| Failure | Fix |
|---|---|
| Invalid JSON in `packs.json` | Restore valid commas and quoting, then parse and inspect the edited object. |
| Router omits a catalog member | Add the matching member line and re-check both lists. |
| Manifest is stale | Update the entry manually from `packs.json` and the leaf frontmatter, then compare both surfaces. |
| Unsafe description frontmatter | Wrap descriptions containing `: ` in double quotes. |
| Leaf has grown into a ledger | Move module status and wave evidence to `.pi/work/`; keep only routing, map, provenance, full graph view, and boundaries. |

## Red flags

- Editing catalog files for a rewrite with unchanged membership.
- Leaving a loader or map reference without a matching capsule.
- Treating a graph result or a missing runner as proof of behavior.
- Closing a work record without inspected source, test, coverage, and diff evidence.
