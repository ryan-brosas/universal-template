# Durable Fabric actors

Inspect the live actor before attaching a capability or deleting it. Installed
Fabric agent docs and the current `agents.remove` schema own call shapes; this
note does not replace them.

## Inspect before adapting

`agents.actors()` and `agents.actorStatus({ id })` are the running definition:
tools, extensions, residency, and delivery. Role markdown in a host-local tree
is a recreation source at best, not the live actor.

A persistent observer with a frozen read allowlist cannot call an MCP server
the coding agent has. Enabling Fabric extensions does not widen `tools`.
Editing a recreation file does not prove the live instructions changed.
Use the installed package's supported update or recreate operation through the
runtime owner, then inspect the live definition again.

If the capability needs tools the actor cannot call, keep it on Main and the
existing playbook. Do not add another orchestration layer to carry it.

## Prove activation, not transport

A mailbox smoke test — create, tell, reply — exercises transport, not the
component event wiring that triggers automatic work, so it cannot support a claim
that an automatic actor works. Before claiming one does, run a fresh-session
lifecycle acceptance: real input plus the settled and compact events must produce
the expected role activations tied to the exact session and checkpoint, including a
silent terminal outcome when that is the correct result. Report transport smoke
separately, do not tell actors manually inside that acceptance path, and do not
let registration or idle status stand in for execution evidence.

## Remove

Confirm the exact actor IDs, owning project, interrupted work and recovery
needs with the user before removal. Read the installed Fabric agents reference,
then describe the live `agents.remove` action. Prefer the typed guest contract (`{ id }`). Extra
fields that discovery lists can still fail the kernel type check.

`agents.remove({ id })` stops and removes a project actor. Durable residency
routes to the resident owner. Confirm with `agents.actors()` that those ids
are gone.

Host-local artifact deletion is a separate scope: enumerate exact role/setup
files and actor/residency directories, preserve any needed recovery copy, and
obtain approval before deleting them. Removing an actor does not authorize
wiping a crew tree or shared mesh log. Leave unrelated actors, Hindsight, host
Fabric/Fovea configuration, prompts and skills untouched.

One-shot child runs use `agents.cleanup`, not `remove`.

## Limits

This does not create a crew, rank models, or authorize deleting another
project's actors. Mesh state keys may remain after a successful remove.
