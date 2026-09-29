---
title: managed-agent-runtime-diagnostics
summary: "Use when an isolated agent worker reports a managed RPC timeout or bridge rejection, long conversations produce truncated replies, or background compaction fails. Supplies safe saved-context probes and traces transport, model metadata and supervisor contracts across the broker/worker boundary."
kind: playbook
---

# Managed-agent runtime diagnostics

A healthy API and a successful short completion do not prove that a restored
agent turn can finish. Separate the
supervisor, RPC, provider and conversation failures before changing a deadline.

## Locate the wait, not just the error

Trace the actual path:

`application → supervisor → isolated worker → model/tool broker → provider`

Record the failing RPC operation, start/end times, last completed event and
correlated run identity. A timeout on `finish` may cover an entire agent turn,
including model retries and tool continuations; it need not mean the IPC channel
or one HTTP request was idle. Read the installed transport and SDK to determine
what each timer covers.

Treat the host CLI, API image, supervisor and worker image as separate installs.
Verify the effective image digest, entrypoint, SDK/extension versions and tool
registration where execution occurs. Installing Pi or Fabric on the host does not
establish that it is installed or enabled in a worker. Distinguish Docker socket
access, container UID/mount permissions and application authorization before
changing any of them.

Use bounded, structured evidence: RPC phase, HTTP status, error code, retry count,
finish reason, token budget and output type/length. Do not dump saved prompts,
tool output, environment variables or credentials to diagnose a control-plane
failure. For auth, record header presence or synthetic-sentinel equality instead.

## Probe without repeating the user's actions

Progress only as needed to distinguish the remaining hypotheses:

1. **Discovery:** call the configured model-list endpoint through the application's
   credential and transport path. A catalog 401 does not establish that inference
   credentials are invalid; discovery and completion routes can differ.
2. **Tiny completion:** test the actual SDK/provider path without tools. Curl
   success proves neither SDK transport compatibility nor managed-worker health.
3. **Saved-context completion:** privately copy the relevant checkpoint and run a
   read-only probe with session writes disabled. Preserve the failing history and
   model settings; a clean thread is a comparison, not a reproduction.
4. **Managed continuation:** run the real worker/broker protocol with synthetic,
   inert tool results and no persistence. Include a continuation when the failure
   happened after a tool call; a single completion omits that part of the context.

Block effects at the executor boundary, not merely with a prompt saying "do not
use tools." Do not replay an uncertain browser, file, email or payment action.
Give probes finite deadlines and verify temporary workers are reaped. Use existing
login/broker boundaries rather than copying host profiles into the sandbox.

## Trace capacity through to the wire

When short prompts succeed but restored conversations truncate or retry, compare:

- Server-declared capacity for the exact selected model and credential.
- Configured/catalog fallback capacity and the broker's resolved model.
- Sanitized worker initialization metadata and persisted model configuration.
- SDK-estimated input, reserved margin, thinking budget and requested output.
- Actual outbound `max_tokens` or `max_completion_tokens`, completion usage and
  finish reason on each attempt.

A server with a large context window can still receive tiny generation budgets if
the SDK believes the model is much smaller. Length-stopped, thinking-only replies
can then drive retries until the parent RPC expires. Inspect the installed SDK's
budget calculation; do not assume a fixed margin across versions, guess capacity
from a model name, reset the conversation, or raise the RPC timeout as the first fix.

Repair the metadata boundary rather than adding a model-specific exception:

- Reuse bounded, authorized model discovery. Fields such as `context_length` and
  `max_model_len` are server extensions, not guaranteed OpenAI-compatible fields.
  Validate positive safe integers and match the requested model ID.
- Keep context capacity and maximum output distinct. Missing metadata remains
  conservative, not unlimited. Identify whether discovery, configuration or a
  fallback supplied the effective limit.
- Where explicit model IDs are supported, unavailable discovery need not disable
  inference. Optional discovery must not bypass inference authorization or swallow
  caller cancellation.
- Scope discovery to the endpoint and credential; deduplicate within that scope.
  Prepare a request-owned model before worker initialization rather than mutating
  a shared catalog object. Preserve conservative pool/fallback limits.
- Keep endpoints, keys and provider headers in the broker. Propagate only the
  capabilities the worker needs, then verify them in the actual worker/checkpoint,
  not only in the discovery parser's return value.

## Test the transport branch that actually failed

`invalid onRequestStart method` or a similar dispatcher error can indicate a
mismatch between Node's bundled fetch implementation and an external Undici
Agent. An IP-literal probe may pass while hostname requests fail because only the
hostname branch creates the custom DNS dispatcher.

Use compatible fetch/Agent implementations and handle Request branding explicitly.
Preserve method, body, cancellation and header-override semantics; in particular,
`init.headers` replaces Request headers rather than implicitly merging them.
Exercise URL and Request inputs, hostnames and IP literals, and the real streaming
SDK. Check both discovery and inference callers: an explicit legacy fetch argument
can defeat a repaired default.

Keep DNS/address validation, redirect restrictions, keyed-transport policy and
response/dispatcher cleanup intact. Making a request succeed by bypassing the
security wrapper is not a transport repair. Use loopback fixtures with synthetic
credentials for wire assertions, never real credentials sent to a test destination.

## Follow background jobs across the same admission boundary

If chat works but compaction or another background task gets HTTP 400, inspect the
supervisor's identity schema before blaming the model. Synthetic run IDs must obey
the same character set and length limits as foreground IDs. Separators valid in a
queue key or log label may be invalid in worker identity headers.

Fix the ID producer, preserve deterministic identity semantics, and test the
consumer's contract. Do not loosen supervisor validation to admit an accidental
format. After repair, verify the job was admitted and completed and its durable
cursor/summary advanced; an enqueue receipt alone is not evidence of compaction.

## Verify without confusing repair, deployment and delivery

Pair focused regressions with a complete real-worker turn through the broker,
including a tool result, checkpoint and cancellation/reaping where relevant. Test
invalid metadata, optional discovery, credential separation and revoked permission.
An HTTP emulator must implement discovery GETs separately from completion POSTs;
parsing every request as chat JSON can cause unhandled errors despite green test
assertions. Inspect the runner's exit status and unhandled-error report too.

Recheck service state before a live probe or rollout. A database hostname failure
such as `EAI_AGAIN` warrants inspecting the database container and network before
changing credentials or schema. Compare exit codes, OOM flags and lifecycle events.
Clean exits or SIGTERM do not identify who stopped a stack; an unexpected stop may
belong to another deployment. Pause for clarification rather than automatically
restarting it. Docker socket permission grants carry Docker-admin power, not just
log-reading access.

Keep source synchronization separate from the running installation. Confirm the
requested fork parent, compare upstream behavior, and preserve deliberate feature
retirements: forward-porting fixes is not permission to restore a removed runtime.
Validate against the target revision's locked toolchain. Do not include deployment
secrets, private probes, database copies or local logs in a public patch.

Report separate states: reproduced, regression-tested, image built, deployed,
original scenario verified, and published. A built candidate is not a deployed
repair. If live verification is blocked, retain the exact recovery state in the
project's existing installation/progress record, not in this reusable playbook.

## Related owners

- [Pi provider contracts](../pi-provider-contracts/README.md) (agent-tooling):
  login, extension registration, catalog refresh and header ordering.
- [Debugging and error recovery](../debugging-and-error-recovery/README.md)
  (engineering): general reproduction and hypothesis discipline.
- [Delivery pack](../../../skills/delivery-pack/SKILL.md): authorized Git,
  publication and deployment work.
