# Verification Recipes

Concrete probes for the pixel-perfect workflow. MCP names follow the Paper/Figma bridge tools; capability-probe the registry before citing a server.

## Enumerating structure under dump truncation
Figma `get_node` dumps get truncated (same node, different lengths between calls). Never parse one truncated dump as truth.

1. Prefer the tool's saved full-output file over a truncated display. Parse complete JSON and check identity and child counts.
2. If no complete artifact exists, request smaller source subtrees. A longer truncated response is still incomplete evidence.
3. Pair visible children by verified identity and order; skip hidden native subtrees when the source omitted them. Treat vector-to-SVG expansion separately.
4. Keep counts and identity mismatches explicit instead of repairing unpaired nodes by guesswork.

## Full-page reference render
- Page nodes often cannot be exported directly ("No nodes to export"). Export each top-level item at a scale that fits (`scale: 0.12` for an 8392px sheet), save into the bridge's working directory (rejects `/tmp`), and view them side by side.
- A node screenshot renders only that node's subtree — overlapping page-level siblings will be missing. Compose mentally by bounds before declaring a difference.

## Font availability (before writing any family)
```bash
curl -s -o /dev/null -w '%{http_code}' 'https://fonts.googleapis.com/css2?family=Decalotype:wght@500'   # 200=exists, 400=no
fc-list | grep -iE 'decalotype|open sauce'                                                              # local check
```
Missing on both → keep the established stand-in family and say so in the report. Never ship a fake token caption documenting the fallback.

## Per-node style diff
- Paper: `get_computed_styles` takes `nodeIds: []` (array). Parse the escaped inner JSON: `JSON.parse(JSON.parse(raw).content[0].text)`.
- Figma: root fills sit in the first `"fills":[` after the node's own `"id"` — regex a bounded window, not the whole dump (child fills pollute global matches).
- Utility classes (`rounded-15xl`, `text-accent-3-500`) must be resolved from a surviving node that uses them — read one computed value per token, never assume a scale step.

## Screenshot sessions
- Whole-artboard shots time out or return empty above ~3000px — shoot per block instead.
- Repeated empty or black captures may indicate a stale session, a render limitation, or a file issue; they do not establish which. Retry once on a bounded target. Then coordinate reconnect/restart if available, protecting unsaved work; otherwise record visual verification as pending.
- Returned image payloads are base64; decode with `base64 -d` and `file` the result before viewing.

## Ghost-hunting
A faint blob without an obvious node is not enough to diagnose an app artifact. Inspect the tree, image fills, effects, clipping, and overlapping siblings. Preserve source-owned effects until a canary isolates the cause. For repair and stale-geometry handling, see `../../pencil/references/component-repair.md`.

## Restore discipline
Capture `get_jsx` of every node before deleting. `write_html` with `mode: insert-children` + absolute `left/top` restores exact positions; keep one write per visual block; de-duplicate by re-listing children after each batch.
