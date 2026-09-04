# Work record: copilotkit (learn --auto pass 1-2)

## Verified pass
Pass 1: eligibility check only; group BLOCKED on missing index. Pass 2 (2026-09-02,
approved --loop run): external restore APPROVED, `ext-copilotkit` indexed full
mode, and the `channels-telegram` grammY long-poll plane mined COMPLETE into
`skills/copilotkit-foundation/references/telegram-long-poll-loop-guard.md`
(loader line + capsule map entry wired in the same tree).

## Source and evidence
- Repository: copilotkit (MIT, LICENSE confirmed at checkout), `main@e9387e04835545c3`;
  checkout `$REFERENCE_ROOT/copilotkit` git rev-parse HEAD == `e9387e04835545c3`,
  origin `https://github.com/CopilotKit/CopilotKit.git`.
- Seam audited and mined: `packages/channels-telegram/src/{listener.ts(599L),
  adapter.ts(742L), types.ts(83L), __tests__/adapter.test.ts(350L)}`: the sequential
  grammY poll loop must never await a blocking agent step (fire-and-forget
  turns, ack-first callbacks, reaction echo guard); capsule pins the ladder.
- Index: `ext-copilotkit` present and ready after the approved restore.

## Decision and counter-evidence
- Pass 1: BLOCKED (identity absent from graph); not auto-indexed; `/learn`
  is not the acquisition gate.
- Pass 2: approved restore resolved the blocker; telegram long-poll seam mined
  to COMPLETE with direct source evidence and a written test-read caveat
  (upstream tests runnable only with resolved workspace deps).

## Next target
Closed for the telegram plane. Remaining copilotkit strands behind a new named
porting question: `channels-discord` render components-v2/modal, teams
download-files/graph-files, whatsapp render/message, core
memory/threads/intelligence/micro-redux state plane, runtime v2
channel-manager fold consumer.
