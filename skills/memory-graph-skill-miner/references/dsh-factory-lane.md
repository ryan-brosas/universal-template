# DSH Factory Host Adapter

Host-specific driver for memory-graph-skill-miner on DSH. The loop contract itself is
host-neutral (see SKILL.md); this file carries only what changes when DSH Factory is
the driving host.

## Surface translation (Hermes → DSH)

Hermes used OpenViking as a second learning ledger and committed from a shared
Pi-template checkout. DSH replaces those surfaces as follows:

| Hermes surface | DSH surface |
|---|---|
| OpenViking llm-repo-learning resource | inspo/.skill-mining-work/llm-repo-learning.md plus each source work record (scheduling/resume surface); OpenViking `viking://resources/llm-repo-learning-passN-<slug>` (semantic search surface, pushed once per pass) |
| foundations-workflow in Pi-template | ~/.agents/skills/foundations-workflow (shared catalog; DSH reads it via the ~/.dsh/skills mount) |
| Pi foundation templates | ~/.agents/templates/foundation-*.md (shared); /home/utopia/.dsh/template/work/project/foundation-*.md are derived mirrors |
| codebase-memory CLI | native, individual Codebase Memory MCP tool calls |
| Hermes cron | DSH Factory recurring task |
| skill_manage / Pi file tools | DSH write, edit, read, grep, bash, and the target skill path |
| shared Pi checkout commit | explicit DSH file writes; commit only if the target is actually Git-managed |

Catalog note: `/home/utopia/.dsh/skills/` is the DSH mount of the shared
`~/.agents/skills` catalog — the same tree, not a fork. Cite either spelling; fix
drift in `~/.agents`.

## Preset rules

Factory configuration is part of the safety boundary: set the task preset to
`standard`, never `fabric` or `code`. The latter presets turn tool use into generated
`run_code` programs and permit exactly the batching shortcut this lane forbids. Keep
one assigned model in the lane; do not delegate to subagents or workflows.

Degraded lock: when the fabric_mesh lease surface is unavailable, proceed under a
degraded lock — exact own-row scoped edits with pre-read and post-write read-back —
and say so in the run report.

## Lane prompt skeleton

Use this as a filled prompt for a DSH Factory learning lane. Keep the target and
allowed paths explicit. The Factory dispatcher only advances the sequential lane;
the source work record and learning ledger are the resume state. This is the
Hermes-style contract: learn first, then produce durable skill knowledge.

    Run the memory-graph-skill-miner workflow as a HERMES-STYLE LEARNING + PRODUCTION BATCH.

    ONE REPO, ONE LANE, ONE AT A TIME: This invocation owns only [source slug] and
    [foundation leaf]. Do not touch other repositories, leaves, or sibling rows.

    CODEBASE-MEMORY MCP IS THE MANDATORY LEARNING SURFACE:
    Start with mcp__codebase-memory__list_projects and index_status; verify graph root,
    branch, HEAD, generation, node/edge counts, and coverage. Learn architecture and
    select seams through get_architecture, paginated search_graph, trace_path, and
    get_code_snippet; use query_graph only for relationships search/trace cannot answer,
    and check_index_coverage before claiming completeness. Do not broadly scan, grep,
    find, cat, or recursively read the repository from the filesystem to build the
    mental model. Direct file reads are allowed only for exact path/symbol/ranges first
    surfaced by MCP, solely to validate a decisive excerpt or direct test; repository
    tests may be executed normally. If MCP is unavailable, stale, incomplete for the
    selected seam, or mismatched to PIN, block and document it instead of falling back
    to direct-file learning. Durable notes and skill files remain the required outputs.

    TARGET REPO: [canonical /mnt/hdd/.../inspo/repo path]
    USER ALIAS: [resolved /home/utopia/work/inspo/repo path]
    TARGET LEAF: [foundation-leaf]
    GRAPH PROJECT: [project]
    PIN: [branch@commit]
    CURRENT STATE: pass [N], [R] references ([V] capsule-v2), next targets [paths/seams]
    COVERAGE: FULL [mode/counts], parse-partial [list], skipped [list], excluded [list]

    RESUME + DE-DUPLICATION GATE:
    Read [inspo-root]/.skill-mining-work/llm-repo-learning.md (row AND Status board line),
    [inspo-root]/.skill-mining-work/[repo]/state.md, research.md, verification.md, the
    target SKILL.md, and every existing reference map entry before selecting work. Build
    a covered/partial/uncited list from those records. Never duplicate a covered seam.
    Refactor or deepen a partial reference instead of creating a twin. If the repo has
    no ledger row, create it in this bounded run.

    PHASE 1 — LEARNING NOTE FIRST:
    Before writing a capsule or refactoring the skill, append a timestamped learning
    note to [inspo-root]/.skill-mining-work/[repo]/research.md. The note must capture the current mental model:
    architecture and subsystem boundaries, important invariants and data/control
    flows, direct-test strategy, the connected subsystem selected for this batch,
    prior coverage consulted, candidate seams (covered/partial/uncited), and the
    exact porter questions to answer. This is the durable explanation of what was
    learned so the next run does not repeat the study.

    PHASE 2 — DURABLE PRODUCTION BATCH:
    Study the selected connected subsystem through Codebase-Memory MCP architecture ->
    paginated graph search -> traced neighborhood -> MCP code snippets -> only then exact
    bounded source/test validation -> MCP coverage checks. Then produce 5–8 distinct durable outcomes in
    this same run (target 6): new capsule-v2 references and/or substantive,
    source-confirmed refactors that close real coverage gaps. Every outcome must
    contain the canonical Source, Path/Symbol, Signature, Data Shape, decisive source,
    Flow, Invariant, executed Probe, live Retrieve call, and Adopt/Adapt/Omit Verdict.
    Do not pad with shallow summaries, duplicate references, or invented evidence.
    If fewer than five genuinely uncited/refactorable seams remain, record evidenced
    closure; if a blocker prevents five, record the blocker and remaining targets.

    REFACTOR RULE:
    Inspect SKILL.md, loader, Capsule map, provenance, and existing references as a
    system. Merge overlapping capsules, repair weak citations, split overloaded
    questions, rename misleading files, and update the map whenever the new learning
    proves the current skill shape is wrong. Do not merely append documents.

    PHASE 3 — OPENVIKING SYNC:
    memadd the learning note and new capsule files into
    viking://resources/llm-repo-learning-passN-[repo]/; verify one newly cited symbol
    with memfind/memread and record the probe. Daemon unreachable ⇒ record the
    degraded path and continue; never block the pass on OpenViking.

    PHASE 4 — VERIFY + RESUME STATE:
    Run every cited Probe and Retrieve, direct tests or honest runner-block probes,
    graph coverage checks, RED/GREEN or deterministic pressure tests, and final
    leaf/map/disk parity. Then update state.md, research.md, verification.md, and
    only this source row AND its Status board line in llm-repo-learning.md with pass,
    batch outcome count, cumulative refs/v2, modules mined/omitted with reasons,
    blockers, exact files changed, and concrete NEXT-PASS TARGETS. The learning note
    must precede the production edits and the ledger/work-record counts must agree.
    If the ledger is not updated, the pass is not delivered.

    GATES: foundations-workflow seven gates; MCP get_code_snippet source evidence wins
    over graph metadata; bounded direct reads may validate only MCP-selected excerpts;
    missing MCP or runners are blocks; execute every Probe and Retrieve; inspect final
    diff and parity.

    WORK-RECORD LAYOUT: New records go under [inspo-root]/.skill-mining-work/[repo]/.
    Never create sibling [repo]-work directories. The layout migration is complete; legacy
    records are archived history, not write targets. If one reappears, stop and repair the path.

    ALLOWED FILES ONLY:
      - /home/utopia/.dsh/skills/[foundation-leaf]/**   (== ~/.agents/skills/[foundation-leaf]/)
      - [inspo-root]/.skill-mining-work/[repo]/state.md
      - [inspo-root]/.skill-mining-work/[repo]/research.md
      - [inspo-root]/.skill-mining-work/[repo]/verification.md
      - [inspo-root]/.skill-mining-work/llm-repo-learning.md, only this source row + board line
      - /home/utopia/.dsh/skills/[foundation-leaf]/SKILL.md, only this genuinely new leaf

    MANUAL LEARNING / NO-SHORTCUT BOUNDARY: Use native individual MCP and file-tool
    calls. Never use run_code/code-mode programs, helper or generated scripts,
    Python/Node/Ruby/Perl one-liners, shell loops, heredocs, xargs/find pipelines,
    awk/sed/jq transforms, temporary automation, or generated arrays of tool calls
    for discovery, extraction, selection, counting, parity, authoring, or verification.
    Do not delegate to a subagent or workflow. For EACH candidate seam, hand-run the
    graph search, trace, snippet, coverage, exact source read, and exact test read,
    then manually author its note/capsule with write or edit. Broad grep/glob may only
    locate an already-named file; it cannot build the repository mental model. Shell
    is permitted only for an existing repository-owned test/check command and exact
    git status/diff; it may not write files or discover/summarize source. Never git
    stash. If a target is Git-managed, stage only owned paths and verify HEAD content.
    If a result cannot be produced without a forbidden shortcut, record partial or
    blocked work instead of weakening this boundary.

    CODEBASE-MEMORY CACHE: Use only the injected canonical MCP server. Never launch a
    second CBM process, derive CBM_CACHE_DIR from command output, or use whitespace-tainted
    cache paths. If MCP reports a cache-root conflict, record a blocker and stop.

    DOUBLED ENFORCEMENT CHECKPOINT (SKILL + TASK MIRROR):
    Before exploration, confirm this task uses the standard preset, name this one repo
    and connected subsystem, and commit to native individual MCP calls. Before success,
    enumerate EACH seam's graph search, trace, snippet, coverage check, decisive source
    read, direct test read, and manually authored file; explicitly certify that no
    run_code/code-mode program, script, pipeline, bulk generator, or delegation was
    used. A shortcut-tainted artifact does not count: redo it manually or mark the run
    partial/blocked. The skill-level rule and this task-level rule are cumulative;
    neither can override the other.

    DELIVERY: learning note -> 5–8 evidence-backed skill/reference outcomes or
    evidenced closure/blocker -> refactor/map parity -> OpenViking sync -> verification
    -> ledger, board, and work-record update. Report exact paths, batch count, evidence,
    blockers, and next targets. Return [SILENT] only when the repo is fully covered and
    the records prove there is no uncited or refactorable reusable seam left.

## Deployment guard — 270 one-repo workers, at most 50 concurrent

The current production topology has the original 97 already-indexed repositories plus
a 173-repository expansion flow. Each Factory task permanently owns exactly one source
checkout, Codebase-Memory project, and foundation leaf. An expansion lane must FULL-index
only its own missing project and verify root/branch/HEAD/coverage before learning. Factory
may run at most 50 mining tasks concurrently, but no task may study multiple repos or skip
the complete index/verify -> learn -> notes -> skill/reference -> verify -> document
sequence. Codebase-Memory MCP is mandatory; direct filesystem scans are never a fallback.
FAC-111 (the original single sequential worker) is retired.

## Fleet mode (50 concurrent one-repo lanes)

Every active per-repo task adds these bindings on top of the single-lane contract:

    FLEET BINDINGS:
    1. LANE OWNERSHIP is exclusive and permanent: mine ONLY the single repository
       named in the task prompt. Never index, study, or create capsules for a foreign
       repository or sibling lane.
    2. LOCK PROTOCOL (LEASE, NOT FOREVER-LOCK): before studying a repo, read
       `skillmine/lock/<repo>`. If absent, claim with CAS CREATE (revision 0 -> 1).
       If present and `{ released: true }`, or its `at` timestamp is older than 90
       minutes, CAS-replace it at its observed revision with your new lease. Only a
       fresh (<90 min), unreleased holder means another live run owns the repo: skip
       to your next owned repo. Include `{ claimedBy, at, expiresAt }`; after ANY
       terminal outcome (success, blocker, or provider failure), CAS-mark it
       `{ released: true, releasedAt, previousClaim }`. This prevents a crashed or
       503-failed pass from permanently blocking future automatic retries. If
       fabric_mesh is unavailable, proceed (shard lists already prevent overlap)
       and say so in the run report.
    3. LEDGER DISCIPLINE: in llm-repo-learning.md, replace ONLY whole rows of owned
       repos, one exact-match row replacement each, plus the owned Status board line.
       Never rewrite, reorder, or reformat other rows; never regenerate the table.
    4. SELECTION: per run, mine the owned repo with the LOWEST pass number (ties:
       alphabetical). One repo per invocation, exactly like single-lane mode.
    5. LEAF MEMBERSHIP: when adding a genuinely new leaf under
       /home/utopia/.dsh/skills/, re-read the destination SKILL.md immediately before
       a single-line insert to minimize concurrent-edit loss.
    6. RATE-LIMIT POSTURE: on provider throttling, back off and continue within the
       run; Factory retries orphaned runs up to maxAttempts (currently 100).
    7. ABSOLUTE-PATH DISPATCH: isolated lanes may dispatch you into a scratch
       worktree of ~/.dsh. Treat cwd as scratch: write ALL skill, ledger,
       and work-record outputs through their absolute live paths
       (/home/utopia/.dsh/skills/..., /mnt/hdd/utopia/inspo/.skill-mining-work/...). Never write via
       cwd-relative paths and never commit or merge the worktree.
