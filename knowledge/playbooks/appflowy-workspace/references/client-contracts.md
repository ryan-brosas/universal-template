# AppFlowy client contracts

Read the installed implementation at the seam you need. These are failure patterns and useful symbol names, not a frozen API schema or permission to make external changes.

## Capability and authentication

CLI, MCP and the service can expose different operations and maintain separate authentication state. Verify the requested operation and connection rather than repeating a failed call or generalizing a client's limitation to the product.

When the CLI works but MCP reports unauthenticated, use the client's supported host-side credential loader or authentication flow. Keep tokens and passwords out of model-visible arguments, logs and artifacts. A working authenticated client can be reused within the user's authorization; an access denial is not a reason to circumvent permissions. Use live help and schemas for current commands and transport details.

In the inspected `appflowy-cli`, `save` and `import` create pages; they do not edit
the addressed page. A successful read does not establish update capability. Check
current help and the owning command before writing, and do not create a replacement
page to simulate an update. If the workspace permits only that CLI, report the
missing operation and prepare the precise proposed change instead of bypassing it.

## Verified MCP operations (2026-10-01 cutover)

In this host the workspace moved from `appflowy-cli` to the packaged MCP server `appflowy` of `appflowy-mcp`; the separate CLI tool was removed after the move was verified. Authentication uses the server's host-side environment loader: `APPFLOWY_EMAIL` and `APPFLOWY_PASSWORD` in the host MCP config (`~/.pi/agent/mcp.json`, mode 600). The first tool call auto-logins, so no separate login step exists; the password never belongs in model-visible arguments, logs or transcripts.

Observed working shapes: `appflowy_append_markdown_to_page` takes `workspace_id`, `page_id` and `request` whose single field is `content`; `appflowy_export_page` takes `workspace_id`, `page_id` and `request.path` and writes a local Markdown readback; `appflowy_list_rows`, `appflowy_create_row` and `appflowy_upsert_row` address databases; `appflowy_move_page_to_trash` and `appflowy_list_trash` cover deletion and recovery. Treat any of these as unverified until the page or row is read back.

Limits: appends are additive at page level. Existing blocks cannot be edited, reordered or deleted, so a correction is appended as a dated note that states what it supersedes. Page trash, restore and row writes exist but need explicit authorization each time.

Row writes: in the inspected `appflowy-mcp` 0.7.3, `appflowy_create_row` accepts plain values keyed by field name, and single-select cells accept the option name (verified by readback). `appflowy_upsert_row` addresses a row only through its `pre_hash`, and no installed read path exposes a row hash; using the displayed row UUID as that key creates a duplicate. Treat status updates on existing rows as manual-in-app work until a client exposes the hash, and remove duplicates by hand.

Two operational traps. After the server environment changes in the host config, a running client can keep the old values until the server process restarts or the session reloads; a direct stdio handshake against the server binary distinguishes bad credentials from a stale client. And the adapter connection is session-local: another agent or host process does not inherit it and needs its own MCP-capable client, the same server entry and the same host-side credentials.

If the current session exposes no named MCP tools, check for an installed native
client before proposing setup. On the inspected host, the `appflowy-mcp` environment
already included `fastmcp`, although it was absent from `PATH`. From the directory
containing the existing `mcp.json`, its `call project:appflowy <tool> ... --json`
route selected that server and loaded its host-side environment without copying
credentials or configuration. Use the installed executable and live help; verify
account and workspace with harmless reads before an authorized write. This local
route depends on the host and does not establish cloud access.

A raw `appflowy_get_collab` error saying no document collab did not establish that
the page was missing: `appflowy_get_page` and `appflowy_export_page` still returned
the existing content. Check those supported page paths before recreating or
repairing anything. After an additive write, a fresh export can verify the exact
appended text occurs once and the previous content remains intact.

## Work-email evidence through local Composio

Missing hosted Composio tools do not establish an OAuth failure. When local access
is authorized, check the installed CLI's help and existing connections before
proposing setup. `composio connections list --toolkit gmail` returns account
selectors and status. `ACTIVE` alone does not identify a mailbox, and a null email
from `composio whoami` was not evidence that connected Gmail accounts were unusable.

Resolve candidate identities with the supported read-only profile request:
`composio proxy https://gmail.googleapis.com/gmail/v1/users/me/profile --toolkit gmail --account <observed-selector>`.
Pin the verified work selector on every search, fetch and approved send; do not search
a personal inbox to infer the work account. Read the live tool schema, search with
a small metadata-only result set, then fetch full bodies only for selected messages.
Keep account selectors, addresses and private message contents out of skill examples.

Large CLI results can return `storedInFile` and `outputFilePath` instead of inline
`data`. Read the returned result artifact before concluding that messages are
missing; inspect only the selected thread and relevant fields.

For an approved in-thread reply, verify the returned message ID in the original
thread, its sender and sole intended recipient, any Cc/Bcc, and `SENT` state.
The inspected reply tool rendered plain input as `text/html` and appended quoted
history. Compare the new authored portion with the approved body, accounting for
line-break markup; quoted text is not evidence that the new reply contains it.
Read back an uncertain send before retrying. `SENT` verifies sending, not receipt
or acceptance; log the verified event once in the canonical record.

For the AppFlowy note, use sender-confirmed status with dates and source links.
Keep a listing confirmation distinct from independently inspecting the public page
or measuring referrals/conversions. A request for a backlink or missing product
detail is a follow-up, not a commitment or permission to send. Resolve the current
record from its content and stable ID; a higher page number alone is not proof.

## Document identity and safe retries

Some page-creation APIs independently default `collab_id` to a new UUID and `view_id` to that collab ID. Supplying only `view_id` breaks the pairing: the folder entry exists, but opening its document fails. Supply both IDs when overriding either for a normal document. The installed `create_page_with_blocks` helper may already enforce this; inspect and reuse it.

Keep receipts of returned IDs. Read the document through the page-view endpoint before bulk moves. After a partial failure, inspect existing objects and resume missing steps, not the whole creation batch. Never recreate an already populated parent merely to initialize its document. If safe document-only initialization is unavailable, leave the hierarchy intact and report the blocker. Do not guess at old binary encodings, enum values or collab-response wrappers. Orphan cleanup requires identified objects and its own authorization.

## Existing rows and native views

An upsert accepting `pre_hash` can derive identity from the workspace, database and key rather than target the displayed row ID. Using an arbitrary row UUID as that key can create a duplicate. Use upsert only when the original key's identity mapping is established. A supported stable-ID edit should preserve unrelated fields and row membership.

Native calendar creation may exist behind a page/database API even when no calendar-specific MCP tool is exposed. Confirm the installed creation contract. Folder layout, database-view layout and field types may use different enums. Verify the Date field, timezone and all-day representation with readback on the intended day, not just a stored timestamp.

## Select fields that appear empty

An empty `type_option` response does not prove a select has no categories. Compare the field reader with the underlying metadata through a supported read path. In an observed backend, `type_option.<field-type>.content` held a JSON object while the reader expected JSON text, so existing options disappeared from normal reads and name-based cell writes could stay blank. Confirm the current reader contract before normalizing anything.

Also inspect required option identities. A list containing only names can still be invalid after serialization because the option reader requires `id`. Preserve existing names, order, IDs and colors. If a duplicate legacy field lacks identities, derive them only from a verified matching definition within the current contract, not arbitrary labels or guessed mappings. Apparent duplicate fields need semantic inspection; do not delete or merge them merely to repair a cell.

Treat metadata repair as a scoped operation, not a speculative write probe. Do not broaden a record update into a database-wide repair without authorization. Snapshot the affected metadata, rows and membership; dry-run the smallest change and, for an incremental collab update, replay it on a copy before applying it. Guard against concurrent changes and verify both normal field reads and target cell reads afterward. Leave unrelated selectors and view settings alone. Prefer ordinary stable-ID cell updates once the field is readable.

Inspect the live collab response shape before decoding. Some deployments expose `doc_state` directly under `data`, rather than under an `encode_collab` wrapper. Never replace a full database merely because a client helper does not recognize the wrapper. Keep credentials and private row data out of diagnostics.

## Content and assets

Build new documents in one ordered pass when practical. Appending nested blocks or tables can misorder content in some clients. This is not a reason to replace existing pages: inspect actual block order, prefer targeted edits, and use an additive index when preserving historical material. If prepending navigation, verify the original block IDs, text and relative order survive.

For Markdown plus local images, use an installed import helper with asset upload enabled and paths relative to the Markdown file. Upload APIs can require the destination page UUID as `parent_dir`, not an arbitrary folder name. Trash is not proof that uploaded blobs were removed.

Document export and database reads are different surfaces. Verify ordered headings, images and link targets for documents; verify IDs, cells, settings and membership for databases. Fetch authenticated assets through the client without exposing its bearer token.
