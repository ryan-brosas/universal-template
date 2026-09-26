# AppFlowy client contracts

Read the installed implementation at the seam you need. These are failure patterns and useful symbol names, not a frozen API schema or permission to make external changes.

## Capability and authentication

CLI, MCP and the service can expose different operations and maintain separate authentication state. Verify the requested operation and connection rather than repeating a failed call or generalizing a client's limitation to the product.

When the CLI works but MCP reports unauthenticated, use the client's supported host-side credential loader or authentication flow. Keep tokens and passwords out of model-visible arguments, logs and artifacts. A working authenticated client can be reused within the user's authorization; an access denial is not a reason to circumvent permissions. Use live help and schemas for current commands and transport details.

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
