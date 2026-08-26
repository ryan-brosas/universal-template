# audit - pattern audit contract

Applies to workflow-lifecycle command audit. Source prompt: ~/.agents/prompts/audit.md. Read-only.

## Goal
Find every occurrence of a code pattern, grade it for correctness/security/edge cases, then produce a prioritized remediation list.

## Phase 1 - Discover
Tool choice per pattern kind:
- Symbol/API: memory-graph search/trace for coverage; memgrep for exact symbols across indexed corpora.
- Structural (try/catch, error-return): regex over bounded dirs; graph where callers matter.
- Literal/text: text search over bounded paths; memgrep for indexed inspiration repos.

Group by subdirectory; record file:line + one line of context; include common variants; when subagents are available fan out bounded read-only scans (concurrency 2-4).

## Phase 2 - Grade
Read 10-30 lines of surrounding context per match. Severity:
- Critical: security hole, data loss, crash on the main path
- Important: wrong behavior on production paths (swallowed error, missing cleanup, off-by-one)
- Minor: style, dead code, debug leftover
- Correct: appropriate use

Security-sensitive patterns: check validation + authz + error handling before grading. Context decides, not the match line.

## Phase 3 - Synthesize
Order by severity then blast radius; propose concrete fixes with file:line anchors for Critical/Important.

## Phase 4 - Report
1. Pattern; 2. occurrences/files; 3. severity counts; 4. Critical/Important issues (file:line, problem, why it matters, proposed fix); 5. correct uses briefly; 6. coverage (searched vs skipped). Report writes require approval.

## Related
research / create / verify complete the loop.