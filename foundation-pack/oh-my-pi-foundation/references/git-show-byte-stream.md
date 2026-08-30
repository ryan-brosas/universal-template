<!-- capsule-v2 -->
# git show byte stream — how do you stream a subprocess's stdout chunk-by-chunk while preserving the caller's timeout/truncation error contract?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What does `runByteStream` guarantee about error fidelity, byte caps, and child lifetime when the consumer abandons or exceeds the stream?

## Streaming twin of runText
**Path/Symbol:** `packages/coding-agent/src/utils/git.ts:` `runByteStream` (:599–687), `GitShowStreamOptions` (:53–57), `show.stream(cwd, revision, options)` static (:1848–1856), error constants `GIT_COMMAND_TIMEOUT_EXIT_CODE = 124` (:273) / `GIT_SPAWN_ENOENT_EXIT_CODE = 127` (:279).
**Signature:** `async function* runByteStream(cwd, args, options): AsyncGenerator<Uint8Array>`; `stream(...): AsyncGenerator<Uint8Array>` (readOnly, `--format=` passthrough, `maxOutputBytes` cap).
**Data Shape:** Yields raw stdout chunks; throws `GitOutputTruncatedError {exitCode, stdout:"", stderr, truncated:true}` on cap breach; `GitCommandError` for timeout/non-zero exit — identical shapes to the buffered path.

### Decisive source
```ts
bytes += value.length;
if (bytes > maxOutputBytes) {
	await terminateTimedOutChild(child);
	settled = true;
	const capturedError = await stderrPromise;
	throw new GitOutputTruncatedError(args, { exitCode: child.exitCode ?? GIT_COMMAND_TIMEOUT_EXIT_CODE,
		stdout: "", stderr: capturedError.text, truncated: true });
}
yield value;
...
finally {
	reader.releaseLock();
	if (!settled) await terminateTimedOutChild(child);   // abandoned generators still kill the child
	void stderrPromise.catch(() => undefined);
}
```

**Flow:** spawn (ENOENT mapped to the same GitCommandError shape with cwd-aware message) → stderr drained concurrently via capped text reader; exit awaited WITH timeout → each stdout chunk: accumulate count, breach ⇒ kill child + truncated error at ITERATION time (never after), else yield → clean EOF: await exit; timedOut ⇒ 124-shaped GitCommandError; non-zero ⇒ stderr-bearing GitCommandError.
**Invariant:** "Stream stdout chunks while preserving the normal git timeout/error contract" (:596) — consumers can switch between `show()` and `show.stream()` without new failure modes. Truncation surfaces AT iteration time because "consumption is the contract" (test comment); the cap is checked BEFORE yield so an over-cap chunk never reaches the caller. The `finally` guarantees no orphaned git process when the generator is garbage-aborted mid-stream. ENOENT keeps the spawn-failure taxonomy (127 + "git is not installed." vs missing cwd).
**Probe:** `packages/coding-agent/test/utils/git-show-stream.test.ts` — `"reassembles the exact blob bytes"` pins chunk-concat ≡ original file bytes (2,000-line emoji content); `"rejects output beyond the completeness cap"` pins `rejects.toThrow(GitOutputTruncatedError)` with `maxOutputBytes: 128`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "runByteStream show stream GitOutputTruncatedError", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `runByteStream git.ts:599-687`, `GitOutputTruncatedError.constructor :203-211`.

## Verdict
Adopt the generator-plus-guaranteed-kill pattern for any large-subprocess streaming; adapt caps/timeout constants to your host. Keep truncation-as-exception-at-iteration (a silent tail-drop would corrupt diff views). Omit Bun-specific ReadableStream instanceof checks if your runtime differs — but re-prove child termination in your finally.
