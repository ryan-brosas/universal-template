<!-- capsule-v2 -->
# Arm-sample inheritance — launching a comparable experiment arm from a sibling's recorded config

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When a user adds "one more arm" to a running benchmark experiment, how do you guarantee the new arm runs the SAME task sample and scale as its siblings — so results are comparable — while only the per-arm knobs change?

## Template scoring + include-vs-observed sample fallback + org-prefix re-derivation
**Path/Symbol:** `packages/metaharness/src/server.ts`:`resolveArmLaunch` (119-186).
**Signature:** `export function resolveArmLaunch(store: RunStore, experimentId: string, req: AddArmRequest): LaunchRequest` — throws when the experiment has no runs or the `<exp>-<arm>` job name is taken.
**Data Shape:** sibling template = an existing `RunRow` whose `config_json` holds a prior `LaunchRequest`. Sample sources in priority order: caller-provided `include` → longest recorded `config.include` → observed trial task names. Job name becomes `${experimentId}-${arm}`.

### Decisive source
```ts
// Template = the sibling whose recorded `include` list is the longest (the
// fullest expression of the experiment's sample — partial re-run arms
// record subsets); among include-less siblings, the most observed trials.
const score = (r: RunRow): [number, number] => {
    const recorded = recordedInclude(r).length;
    return recorded > 0 ? [1, recorded] : [0, store.listTraces(r.jobName).length];
};
// Exact task sample: prefer the intended include list, else observed trial
// tasks. Trial task names are stored bare, while org-prefixed datasets
// (e.g. "swe-bench/swe-bench-verified") address tasks as "<org>/<task>" —
// re-derive the prefix for the fallback.
let include = req.include?.length ? req.include : strings(cfg.include);
if (include.length === 0) {
    const org = template.dataset.includes("/") ? `${template.dataset.split("/", 1)[0]}/` : "";
    include = [...new Set(store.listTraces(template.jobName)
        .map(t => t.task).filter(Boolean)
        .map(task => task.includes("/") ? task : `${org}${task}`))];
}
```

**Flow:** validate arm token `[A-Za-z0-9_.-]+` and required model → find siblings via `experimentOf(jobName) === experimentId` → pick the template by score (recorded include beats trial count; ties keep the newest since `listRuns` is newest-first) → inherit benchmark/dataset/concurrency/timeout/attempts/agent/webSearch/conditions/environment verbatim from the template config; take model/prewalk/role/note/extraArgs ONLY from the request → resolve the exact sample (request > recorded > observed with org-prefix re-derived) → set `tasks = include.length` when a sample exists ("an explicit include list IS the sample — never let the runner's default task cap truncate it"), reject if `<exp>-<arm>` already exists → launch through the normal path.
**Invariant:** comparability is structural, not conventional: everything that affects difficulty (dataset, sample, scale knobs) comes from the sibling record; only treatment knobs come from the caller. A partial re-run arm must never become the sample source over a sibling with the full recorded list.
**Probe:** `packages/metaharness/test/manager.test.ts:468-551` — `inherits dataset + exact task sample + scale from a sibling arm`, `prefers the sibling with a recorded include list over newer include-less siblings`, `rejects a duplicate arm and an unknown experiment`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveArmLaunch AddArmRequest experimentOf template include", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any A/B experiment launcher: derive the control variables from the sibling row, diff only the treatment knobs, and prefer the recorded intent (`include`) over observed outcomes when reconstructing samples. Adapt the LaunchRequest field set and naming grammar to your system; omit nothing else. Three direct unit tests pin inheritance, template preference, and rejection paths.
