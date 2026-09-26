# Move a team without mixing workspaces

Use for agent profiles, rooms, and associated state. Agree whether "move" means
reparenting existing objects or creating dedicated copies and retaining originals
as archives. Empty new rooms are not migrated conversation history. Explain the
blast radius and obtain approval before live mutations or archival.

## Scope before writes

Bind each manifest to the intended workspace ID, with a name check when useful.
Validate that identity before scoped reads or writes; carry explicit scope on
every resource request rather than relying on the UI's current selection. A
space-agnostic discovery call is a legitimate preflight exception. Missing or
unexpected identity stops the operation; do not fall back to Personal/default.

Snapshot source IDs, settings, memberships, active work, and the history fields
needed for the preservation claim. Keep that baseline immutable. Record desired
destination differences separately: changing a destination pin is not permission
to rewrite the source baseline or silently accept drift.

Use an allowlist for profile copies. Do not copy memories, conversations, files,
routines, secrets, or connectors merely because they are reachable. Workspace
scoping does not prove credential or host-tool isolation; verify each claimed
boundary independently.

## Reconcile and recover

Use one scoped driver with per-workspace manifests. Reject duplicate or ambiguous
identities instead of adopting a same-named object. Skip unchanged writes:
seemingly harmless membership updates may recreate rows, reorder recipients, or
cancel work. Keep original and destination identifiers disjoint when copying.

Journal each committed operation and source-to-destination mapping. Exercise
resume after partial progress, not only a second run after success. After an
error, inspect authoritative state before retrying: mutation may have succeeded
while its readback failed. Archive only the approved originals, after destination
verification and the required idle check. Retire superseded scripts that could
recreate the old placement.

## Match the proof to the claim

- Compare exact expected sets, including missing objects, not just totals or the
  objects still returned. List permitted archival deltas explicitly: an API may
  clear a pin, and restore may not reinstate it.
- Check archived-read semantics before cutover. An active-only getter can refuse
  a successfully archived object. Use the supported archived listing or, when
  authorized and necessary, a read-only database query; do not unarchive merely
  to inspect it.
- Counts and hashes over IDs, order, and roles prove only those fields. To claim
  content preservation, compare the relevant content and attachments across all
  pages using a stable representation. Do not call a metadata digest
  "byte-identical history" or treat one page as the full thread.
- Verify destination-scoped queries and the actual UI route. A cross-workspace
  sidebar may intentionally show other workspaces' names; attribute each entry
  to its owning group rather than equating visible text with shared access.
- Generate report identifiers from the journal and mechanically compare them.
  Keep validator expectations independent of the candidate being installed.

Rollback should restore the intended source state from its snapshot, including
settings that unarchive does not restore. Removing populated destination objects
is destructive; state that separately from restoring originals. A config backup
alone does not undo created bots, rooms, or messages.
