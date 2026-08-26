<!-- capsule-v2 -->
# Docker resource cleanup — targeted reclamation of a crashed benchmark run's containers and networks

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** After a benchmark harness crashes, how do you reclaim its Docker containers and networks — precisely, without touching unrelated workloads or anything still running?

## Project-regex targeting + state-filtered removal + active-project network protection
**Path/Symbol:** `packages/metaharness/src/runner.ts` — `HARBOR_PROJECT_RE` (1428), `listHarborContainers` (1438-1459), `runDockerCleanup` (1468-1526), CLI `cleanup` command (1713-1717).
**Signature:** `function runDockerCleanup(force: boolean): void` — never throws (catch-all warns); also runnable as a standalone `metaharness cleanup` command with force=true.
**Data Shape:** trial compose projects match `/^[a-z0-9_.-]+__[a-zA-Z0-9]{7}$/` (`<task>__<7-char-suffix>`); secondary identity = working_dir containing `.cache/harbor/tasks`. Non-force removable states: `exited|created|dead`.

### Decisive source
```ts
const harbor = HARBOR_PROJECT_RE.test(project ?? "") || (workingDir ?? "").includes(".cache/harbor/tasks");
...
const removable = force ? containers : containers.filter(c => ["exited", "created", "dead"].includes(c.state));
...
// Networks of projects that still have a running container are kept (non-force).
const activeProjects = new Set<string>();
if (!force) for (const c of containers) if (c.state === "running" && c.project) activeProjects.add(c.project);
...
if (HARBOR_PROJECT_RE.test(projMatch[1]) && !activeProjects.has(projMatch[1])) netIdsToRemove.push(netId);
```

**Flow:** list ALL containers once with compose-project + working-dir labels → keep only harbor-shaped ones (project regex OR staged-under-tasks dir) → non-force: remove only those in exited/created/dead states; force: remove everything matching, running included (`rm -f`) → compute the set of projects that STILL have a running container → remove idle harbor networks whose compose project is not in that protected set (non-force; force drops every idle trial network) → per-resource failures are warned and skipped, and any thrown error becomes a warning line, never a crash.
**Invariant:** targeting is two-signal (name shape AND staging path) so unrelated compose projects are untouchable; in non-force mode nothing running is ever removed and no project's network dies while a container of that project lives; cleanup failures degrade to warnings because leftover resources must not block the next run.
**Probe:** no direct automated test (requires a live Docker daemon) — coverage caveat recorded. The regex and state lists are source-read at `packages/metaharness/src/runner.ts:1428,1455,1472`; behavior claims above are source-grounded only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "runDockerCleanup listHarborContainers HARBOR_PROJECT_RE docker network rm", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adapt this one rather than adopt verbatim: the two-signal targeting rule, run-state filtering, active-project network protection, and warn-don't-crash error posture transfer to any orchestrator that leaves Docker debris. The specific compose-label plumbing and the `<task>__<suffix>` naming are host conventions. Recorded honestly: no runner available in CI for live-docker probes.
