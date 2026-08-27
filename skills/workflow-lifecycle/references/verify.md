# verify - pre-claim gate contract

Applies: workflow-lifecycle verify. This reference is the canonical contract (the retired global prompt file is folded into it). Read-only until the final artifact write.

## Phase 0 - Cache
Fingerprint = git HEAD + full diff + untracked contents hash. If it equals the last traced stamp, report cached PASS and skip ahead (unless --no-cache / --full).

## Phase 1 - Context
Read the work spec payload (or agent spec); confirm plan/spec exists and is fully read.

## Phase 2 - Completeness
Every requirement from spec/PRD gets implementation evidence (file:line); mark complete/partial/missing; report score X/Y. Never mark missing without first searching (grep + graph + memgrep).

## Phase 3 - Correctness
Run the repository gates; record a mode column and read the output (not just the exit code). No aggregate gate exists: run git diff --check, inspect every changed call site, parse changed structured data, use the affected skill/source/test evidence. URLs supplement, never replace, local evidence.

## Phase 4 - Record
When green, write the cache line and the durable verification.md (gate table + result). This is a schema-guarded write (or explicit approval).

## Phase 5 - Coherence
Cross-check spec vs implementation vs plan vs research; flag contradictions with file references.

## Phase 6 - Local vs live
Separate verified locally from needs-live-server confirmation; label unverified claims.

## Report
1. Result (READY / NEEDS-WORK / BLOCKED); 2. completeness count; 3. gate table; 4. coherence findings; 5. local-vs-live; 6. blockers; 7. next command.
