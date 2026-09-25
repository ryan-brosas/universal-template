---
title: appflowy-workspace
summary: "Use when organizing or numbering AppFlowy pages, creating native calendars, updating existing records, collecting evidence, or recovering from CLI/MCP authentication, document-identity or ordering failures."
kind: playbook
---

# AppFlowy workspace

Use the installed client, live schemas and matching source. A missing CLI or MCP operation does not establish that AppFlowy lacks the capability. Check supported, authorized alternatives before declaring a limit; do not bypass access controls.

## Start at the right boundary

Inspect the requested subtree and page purposes. Record stable page, view, database and row IDs separately from editable titles. Scope reads to the change: one publication link does not need a workspace-wide investigation.

Organizing navigation is not permission to change task status, ownership or dates, archive old work, or resume a previous campaign. Use the project's current remit and approval rules. Deletion or archival needs its own authorization; a separately approved, backed-up move to trash is still valid.

## Preserve identity before adding structure

- Move and rename existing pages rather than copy them into replacement trackers. A database container and its nested native views are not necessarily duplicates.
- For a new document with an explicit `view_id`, pair `collab_id` with that same ID. Reuse a helper that enforces this contract. Create and open one new parent successfully before moving existing children beneath it.
- If a section appears in the folder tree but cannot open, check document identity before recreating anything. Repair a confirmed missing document at the existing ID through a supported path; do not recreate a populated parent and risk its children.

## Organize the navigation, not just the labels

Use consistent zero-padded prefixes when numbering is requested, then set and read back actual sibling order. Preserve native database tabs and settings unless they are in scope.

Make the hub and section indexes link to the existing records. Clearly separate retained historical notes from current navigation. Update maintained path-based references after renaming; ID-based links should keep resolving. Build new page content in one ordered operation. For existing pages, prefer precise edits or verified additive navigation over rebuilding their contents.

## Deliver a native calendar

A Markdown schedule is not a calendar view. Locate or create the actual database view and verify its Date-field binding, dated rows, timezone and all-day behavior. Distinguish container, view and database IDs. Keep the database canonical rather than maintaining a second live table.

Separate publication status from evidence. A user-reported publication may lack a permalink. Saving a supplied URL can be verified by readback; it does not independently verify the live wording, placement or results. A reshare is not another original piece. Unknown is not zero.

## Update the existing record

Do not assume an `upsert` tool targets a row UUID. A `pre_hash` may derive a different row identity. Check the contract and original key before using it; otherwise use a supported stable-ID update or report the specific blocker. Preserve unrelated cells, patch only necessary metadata and confirm row IDs as well as count.

## Verify what the user will open

Use fresh hierarchy reads and the application's page-read path, not only successful writes or raw storage. Check requested order, readable indexes, original IDs, linked records and unaffected database settings. Compare structured values rather than encoded CRDT bytes.

If unexpected rows or values change during the work, retain the baseline, investigate and report the difference. Preserve unrelated edits; do not restore a snapshot to force a green check or attribute an author without evidence. Qualify completion claims and logs to match what was actually verified.

## References

- [Client contracts](references/client-contracts.md): authentication, document identity, row updates, block ordering and assets.
- [Maintainer checks](references/checks.md): synthetic cases for reviewing changes to this procedure, not a required runtime workflow.
