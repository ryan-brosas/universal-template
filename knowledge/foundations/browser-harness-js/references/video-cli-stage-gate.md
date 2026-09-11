<!-- capsule-v2 -->
# Video CLI stage gate — how do you expose a multi-stage evidence pipeline as a CLI so an agent physically cannot skip a stage?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What CLI grammar makes `init → review → export` an enforced progression rather than three unrelated commands?

## Three verbs, active-recording interlock, first-use-wins option latches, machine-wide lock
**Path/Symbol:** `skills/cdp/sdk/video.ts:runVideoCli` (:626-665), wrapping `withVideoLock` (:594-624); interlock source `recording.ts:activeRecording` (:119-130).
**Signature:** `runVideoCli(args: string[]): Promise<number>` — `[command, path, ...options]`; verbs exactly `init|review|export`, else usage + exit 2.
**Data Shape:** init prints `summary:` + `next:` pointers to the artifacts the NEXT stage consumes (`recording-summary.json` → author `edit-brief.json` → review); export defaults `output='video.mp4'`, `reviewed=false`.

### Decisive source
```ts
const recording = resolve(path);
const active = await activeRecording();
if (active) throw new BriefError(`stop the active recording before video processing: ${active}`);
if (command === 'init') {
  // only --require-explicit is legal, and only once
  ...
  console.log(`next: write ${join(recording, 'edit-brief.json')}, then run browser-harness-js video review`);
}
...
let reviewed = false;
let outputSet = false;
for (let index = 0; index < options.length; index++) {
  if (option === '--reviewed' && !reviewed) reviewed = true;
  else if (option === '--output' && !outputSet) {
    const value = options[++index];
    if (!value || value.startsWith('--')) throw new BriefError('--output requires a value');
    outputSet = true;
  } else {
    throw new BriefError(`unsupported or duplicate export option: ${option}`);   // duplicates are errors, not idempotent repeats
  }
}
return withVideoLock(() => render.exportVideo(recording, output, reviewed));
```

**Flow:** every invocation resolves the recording path and FIRST checks no recording is active (you cannot process while still capturing) → `init` compiles `recording-summary.json` (typing hidden unless `--require-explicit`) and prints the literal next-stage instruction → `review` accepts zero options and renders the interactive reviewer under the lock → `export` parses options with one-shot latches and runs `exportVideo(recording, output, reviewed)` under the same lock. The render module imports lazily (`await import('./video-render.ts')`) so `init` never pays the renderer load.
**Invariant:** THE GRAMMAR IS THE GATE — unknown options, repeated flags, and a value that looks like another flag are all hard `BriefError`s (fail loud, not "last one wins"), so an agent cannot accidentally export unreviewed by mistyping; `--reviewed` exists precisely because the reviewed/unreviewed distinction must be an explicit operator claim at export time. All mutating stages serialize machine-wide through `withVideoLock`'s `wx`-created pid lockfile with stale-pid liveness reaping (`process.kill(owner, 0)`, corrupt owner unlinked and retried), so two concurrent exports can never interleave in one recording dir.
**Probe:** deterministic source pins (CLI dispatch has no dedicated suite): `grep -n "unsupported or duplicate export option\|stop the active recording before video processing" skills/cdp/sdk/video.ts` → :661/:634. Behavioral adjacency: `'recording initialization hides typing and hashes exact evidence'` (`video.test.ts` :46-68) executes `initRecording` + `compileBrief`; lock internals are pinned in `hardened-video-renderer.md` (withVideoLock :594-624). Suite executed GREEN at this pin (17/17, pass 5).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "runVideoCli", limit: 3, fields: ["signature", "name", "file"] });
// EXECUTED pass 5: video.runVideoCli @ video.ts:626-665; trace both directions shows callees activeRecording/BriefError/initRecording/withVideoLock (+safeText/safeLabel/loadJson/sourceFiles via initRecording's cluster).
```

## Verdict
Adopt the verb-gated stage machine (interlock against the live recorder, printed next-stage pointer, duplicate-option rejection, explicit `--reviewed` claim) for any pipeline whose stages have consent or quality semantics; adapt the option set and default output name; omit the lazy renderer import only if your stages share a process anyway. Caveat: no direct test drives arg parsing/dispatch (recorded block — deterministic pins used); `video.ts` coverage no_recorded_issue + metadata_match.
