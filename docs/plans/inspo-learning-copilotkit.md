# Work record: copilotkit (learn --auto pass 1)

## Verified pass
No evidence pass run: eligibility check stopped at index availability.

## Source and evidence
- Repository: copilotkit (MIT, LICENSE confirmed at checkout), `main@e9387e04835545c3`; checkout `/mnt/hdd/utopia/inspo/copilotkit` git rev-parse HEAD == `e9387e04835545c3`, origin `https://github.com/CopilotKit/CopilotKit.git` (verified this pass).
- Seam audit (read-only, source-level): `packages/channels-telegram/src/{listener.ts(599L), adapter.ts(742L), types.ts(83L), __tests__/adapter.test.ts(350L)}`: grammY long-poll integration with loop-guard + group gating, and the CRITICAL invariant that agent turns must never block grammY's sequential poll loop (waitChoice → confirm_write).
- Index: Codebase Memory `ext-copilotkit` is NOT present in the live census (0 hits in list_projects). Index install dir lacks a live `.db`; only the Aug-23 coverage log exists.

## Decision and counter-evidence
- BLOCKED: recorded full index is absent from the graph (same "identity absent" class as framer-motion before its restore). Candidate was not auto-indexed: `/learn` is not the acquisition gate.
- Strand marked seam: `channels-telegram` (6.4kL long-poll listener plane) UNMINED; run-handler mined pass 2.

## Next target
- Route: `/inspo` with candidate copilotkit @ `e9387e0483…` seam "channels-telegram grammY long-poll transport" to approve the index restore; then `/learn --auto foundation-pack continue` resumes this group.
- **Approval needed:** explicit user approval to re-index the existing exact-pin checkout as `ext-copilotkit` (full mode). Approving it unblocks the seam pass; no other gate remains (license MIT, pin verified, tests present at 350 lines, runnable only if workspace deps resolve, otherwise read-as-caveat).
