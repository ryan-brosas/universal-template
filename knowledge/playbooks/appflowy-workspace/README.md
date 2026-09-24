---
title: appflowy-workspace
summary: "Use when driving AppFlowy pages, spaces or database rows from the CLI or MCP, building a work or progress tracker in AppFlowy, capturing screenshot evidence, or recovering from AppFlowy auth, upload, page-order or read failures."
kind: playbook
---

# AppFlowy workspace

AppFlowy is a document-plus-database workspace reached by two clients: `appflowy-cli` and the
`appflowy-mcp` server (FastMCP, stdio). The installed `--help` and live tool schemas own the
current surface; the contracts below are the non-obvious ones that cost rework.

## Treat IDs as identity

Page **titles are hand-editable and drift**; `view_id` and `database_id` are stable. Record and
address those. A cached `tree` can return stale names — prefer `ls`/export for current titles, and
re-read rather than trusting an earlier listing.

## The two clients differ

- `appflowy-cli`: login, workspaces, `use`, `ls`, `tree`, `search`, `export`, `import`, `save`.
  It cannot read database **rows** or move a page to trash. `export` requires an output path.
- MCP server adds rows (`list_rows`, `get_row_details`, `create_row`), trash/restore, reorder and
  upload.

So "the CLI cannot" never means "AppFlowy cannot" — check the MCP surface before declaring a limit.

## Auth

The MCP server keeps tokens **in memory only** and reads neither the CLI's `credentials.json` nor a
password. Supply `APPFLOWY_EMAIL`/`APPFLOWY_PASSWORD`, or call `appflowy_refresh_token` with the
refresh token from `~/.config/appflowy-cli/credentials.json` at the start of a session. Without
that, every MCP tool returns "Not authenticated" while the CLI still works. When the host has not
loaded the MCP tools, the stdio server can be driven directly: initialize (`protocolVersion`
2025-06-18), send `notifications/initialized`, then one `tools/call` per request — key results by
call index, because identical tool names overwrite each other in a name-keyed map.

## Writing pages

- **Build a page whole.** One create call preserves block order; **appending to an existing page
  can scramble order** (tables reversed, sections rotated). Rebuild instead of appending when
  order matters.
- **Import with assets** for text plus local images: `import_markdown_file` with
  `upload_assets: true` uploads images resolved relative to the Markdown file and creates the page
  in a single ordered pass.
- **Uploads need a UUID `parent_dir`** — the destination page's `view_id`, not an arbitrary key.
  A non-UUID key fails with HTTP 404 "UUID parsing failed". Uploaded blobs survive the source page
  going to trash.
- Boards/databases do **not** export as Markdown; read rows through the row tools.

## Track work with evidence tiers

A tracker can show progress and still be wrong about it. Label each item **verified** (screenshot,
export, or receipt attached) or **reported** (a claim with no evidence), and keep `Unknown`
distinct from `0`. Treat funnel stages as separate facts — exposure, engagement, conversation,
signup, first successful use, repeat use — because a like is not a signup and a testimonial is not
usage. Drafts, published work and verified results are three different states.

## Boundaries

Prefer trash (recoverable) over permanent delete, and export a space before clearing it. Keep
credentials out of the repository. Write evidence into the tracker with a caption naming the date,
the source, and the goal it counts toward.

## Verification

Confirm a page by exporting it: headings in order, expected image blocks present, and image URLs
fetching (HTTP 200 with a bearer token). Re-count database rows after any change. A successful
write is not evidence that the page reads correctly.
