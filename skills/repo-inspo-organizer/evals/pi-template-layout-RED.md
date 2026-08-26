# RED pressure scenario: durable per-source work record

## Scenario

The user asks to study one inspiration repository, translate it into DSH, and keep the work resumable across sessions. The agent must use the pi-template-derived durable record while preserving the existing inspiration layout.

## Expected failure without the layout guidance

An agent leaves research in the root, mixes source checkout files with notes, overwrites a single global plan, creates a duplicate inspo tree or a source worktree, and cannot identify the current position or verification evidence after a session break.

## Rubric

Pass only when the agent:

- preserves the established flat or nested library instead of moving or duplicating it;
- keeps the inspiration checkout read-mostly and normally is_worktree=false;
- creates exactly one source card and one durable work record for the source;
- for a graph-only refresh, records source.yml plus work/state.md and work/verification.md without fabricating study conclusions;
- for active study, separates checkout, source card, work, study, excerpts, and comparisons according to the existing layout;
- uses state.md as the current-position handoff;
- records ordered dependencies and acceptance checks in plan.md or tasks.md when the study requires them;
- records actual graph, source, test, and catalog results in verification.md and the appropriate ledger;
- closes the record before starting another source.

A user-authorized batch graph refresh may create one minimal graph-only record per existing source and one GRAPH-INDEX.md ledger, but it must not become a batch study.
