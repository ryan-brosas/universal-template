# Recover ownership from existing durable history

Use when a restart loses transient ownership or recovery state but a durable
session or operation journal already exists. Recover the outstanding obligation,
not an old execution plan. A restart test that retains the original controller
can miss this failure entirely.

## Establish whether the journal is sufficient

Locate the durable record of the successful transition, its identity, the prior
owner or return target, and the event that settles or supersedes it. Confirm these
records belong to the active session or branch. A convenient log line is not
necessarily an authoritative record; check its persistence and retention contract.

If the existing journal provides those facts, derive the missing transient state
and reuse the existing restoration path. Do not add a second completion marker
when the authoritative transition already records completion. If the journal
lacks a required fact, identify that gap rather than inferring it or declaring
all persistence unnecessary.

## Recover only what is still owed

- Validate the latest applicable record and its ownership identity. Ignore foreign
  branches and malformed records; ambiguous newer evidence must not resurrect an
  older obligation.
- Check for subsequent completion, another ownership transition or a deliberate
  user choice. A current value matching an old borrowed value does not mean that
  old obligation is still active.
- Restore only while the resource is still in the state this operation borrowed.
  Recover a return target, not pending work, queued messages or a retired plan.
- Run recovery before initialization that could accept new work or capture the
  stranded state as its new baseline. Reuse the normal restoration path and its
  failure handling; do not replay the completed task to obtain a clean finish.

## Verify the restart boundary

Construct a fresh controller from the saved history, with no retained in-memory
state. Check outstanding, already-completed, superseded, manual-choice, malformed
and foreign-branch cases. Exercise a second restart after successful recovery: it
must not restore again. Check retention or compaction boundaries if they affect
which records recovery can see.

In an authorized isolated live probe, reopen the same session without forcing the
expected owner on the command line. Observe ownership before the first new request
and verify completed effects remain unchanged. A startup override can conceal
missing recovery. Stop only the isolated process approved for the probe.

This method covers transitions whose recovery facts became durable. A crash before
that record exists is a separate gap; proving recovery after the record was saved
does not establish atomicity of the earlier transition.
