<!-- capsule-v2 -->
# gh Subprocess Hermetic-Env Slot Semaphore — how do you bound a CLI subprocess fleet and guarantee it can only use its own stored credentials?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** When a registry client falls back to shelling out to an authenticated CLI (`gh`) under high concurrency, how do you cap the process fan-out and make each invocation hermetic regardless of the parent environment?

## direct-handoff counting semaphore + rebuilt child env
**Path/Symbol:** `packages/shadcn/src/registry/github-cli.ts:withGhSlot` (:147-168), `buildGhEnv` (:170-191), `runGhApi` (:229-257).
**Signature:** `withGhSlot<T>(run: () => Promise<T>): Promise<T>` (module-level `ghSlots = 8`, FIFO `ghQueue` of resolvers); `buildGhEnv(): NodeJS.ProcessEnv`.
**Data Shape:** Two module-level primitives: a slot counter and a promise-resolver queue. The execa call uses `{ env: buildGhEnv(), extendEnv: false, timeout: 15_000, maxBuffer: MAX_GITHUB_SOURCE_FILE_SIZE, stripFinalNewline: false }`.

### Decisive source
```ts
async function withGhSlot<T>(run: () => Promise<T>) {
  if (ghSlots > 0) {
    ghSlots -= 1
  } else {
    // The finisher hands its slot to the woken waiter directly.
    await new Promise<void>((resolve) => ghQueue.push(resolve))
  }
  try {
    return await run()
  } finally {
    const next = ghQueue.shift()
    if (next) {
      next()          // hand the slot straight to the waiter…
    } else {
      ghSlots += 1    // …only return it to the counter if nobody waits
    }
  }
}

// The gh rung must only ever use the stored github.com credential, with
// stable output and no prompts, regardless of the parent environment.
delete env.GH_TOKEN; delete env.GITHUB_TOKEN
delete env.GH_ENTERPRISE_TOKEN; delete env.GITHUB_ENTERPRISE_TOKEN
delete env.GH_DEBUG; delete env.DEBUG; delete env.GH_FORCE_TTY
delete env.GH_TELEMETRY
env.GH_HOST = "github.com"; env.GH_PROMPT_DISABLED = "1"
env.GH_NO_UPDATE_NOTIFIER = "1"; env.GH_PAGER = "cat"; env.NO_COLOR = "1"
```

**Flow:** acquire → either decrement the free counter or enqueue your resolver and sleep → run `gh api --hostname github.com <endpoint> -H Accept… -H X-GitHub-Api-Version…` under the rebuilt env → in `finally`, wake the next waiter by handing over the slot, or increment the counter if the queue is empty. Because `extendEnv: false`, the child sees ONLY the constructed env: all credential variables are deleted (gh then uses its own keychain credential from `gh auth login`), and debug/TTY/pager/telemetry variables are stripped so output is deterministic and parseable.
**Invariant:** At most 8 concurrent gh processes no matter how many items resolve concurrently. A released slot is never double-assigned (hand-off vs counter-return are mutually exclusive). The child can never inherit a token from the parent environment, and cannot hang on prompts or emit ANSI/pager noise.
**Probe:** `packages/shadcn/src/registry/github-cli.test.ts` — :259-281 twenty concurrent fetchGitHubFileViaGh calls observe maxActive ≤8 and >1; :109-149 exact argv + env assertions (GH_HOST pinned, GH_PROMPT_DISABLED/NO_COLOR set, every credential var absent); :151-164 parent GH_HOST/GH_TOKEN/GH_DEBUG scrubbed even when stubbed. Runner caveat: node_modules absent in checkout — pinned by direct reads.
**Coverage:** github-cli.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "withGhSlot gh slot semaphore concurrency buildGhEnv hermetic env", limit: 8 });
// observed: withGhSlot #1 (:150-168), buildGhEnv #2 (:170-191)
```

## Verdict
Adopt the direct-handoff semaphore verbatim for any bounded subprocess pool (it avoids both lost-wakeups and counter drift) and the delete-list + fixed-vars env rebuild whenever a fallback CLI must be forced onto its own stored credential. Adapt the concurrency constant and timeout to your process budget; adapt the deleted-variable list to your CLI's actual env surface.
