# Foundations Workflow — Wiring & Verification

## Wiring

Catalog discovery is filesystem-based: every directory under the catalog root with a valid `SKILL.md` is discoverable. There is no manifest, router, or packs file to maintain.

**Rewrites:** update only the leaf `SKILL.md`, its references, and the durable work record.

### New membership
1. Create the leaf directory under the catalog root (`skills/<repo>-foundation/`) from the canonical template.
2. Verify discovery: the leaf appears in the host skill list immediately after creation (probe it; do not assume).
3. Record the inspected path and probe outcome in the work record.

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
| Leaf not discovered by host | Check folder name == frontmatter `name` and that `SKILL.md` exists at the leaf root; re-probe the skill list. |
| Unsafe description frontmatter | Wrap descriptions containing `: ` in double quotes. |
| Leaf has grown into a ledger | Move module status and wave evidence to `.pi/work/`; keep only routing, map, provenance, full graph view, and boundaries. |

## Red flags

- Editing catalog files for a rewrite with unchanged membership.
- Leaving a loader or map reference without a matching capsule.
- Treating a graph result or a missing runner as proof of behavior.
- Closing a work record without inspected source, test, coverage, and diff evidence.
