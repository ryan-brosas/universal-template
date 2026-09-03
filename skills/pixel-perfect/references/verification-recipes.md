# Verification Recipes

Concrete probes for the pixel-perfect workflow. MCP names follow the Paper/Figma bridge tools; capability-probe the registry before citing a server.

## Enumerating structure under dump truncation
Figma `get_node` dumps get truncated (same node, different lengths between calls). Never parse one truncated dump as truth.

1. Re-fetch up to 3 times and keep the longest raw string.
2. Bracket-scan the top-level `"children":[` — track depth, skip strings with escape handling, collect each direct child as a substring.
3. Per child, regex out `id`, `name`, `type`, `bounds`, and root `fills`.
4. Sanity check: every sibling after the first must appear; if the count changed between fetches, the dump is still truncated.

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
- Empty results across ALL nodes = stale MCP session, not a rendering bug. Restart Paper Desktop / reconnect the MCP plugin once, then retry.
- Returned image payloads are base64; decode with `base64 -d` and `file` the result before viewing.

## Ghost-hunting
A faint blob in the render with no matching node is an app rendering artifact — verify with a full tree summary plus a `find_nodes` sweep for image fills before blaming the file.

## Restore discipline
Capture `get_jsx` of every node before deleting. `write_html` with `mode: insert-children` + absolute `left/top` restores exact positions; keep one write per visual block; de-duplicate by re-listing children after each batch.
