<!-- capsule-v2 -->
# stream-failure-ladder — how do per-side stream failures map to placeholder kinds without killing the whole diff?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** When one side of a streamed file view fails (truncated, git error, aborted), what does the UI show and what must NOT happen?

## #streamGitSide catch + #streamFileSide pre-checks
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/state.ts` (`#streamGitSide` catch block; `#streamFileSide` size/binary checks).
**Signature:** `catch (error) { if (signal?.aborted) throw error; if (error instanceof git.GitOutputTruncatedError) {...} if (error instanceof git.GitCommandError) {...} throw error; }`.
**Data Shape:** Failure outcomes: `GitOutputTruncatedError → stream.markTooLarge(side) + {kind:"tooLarge"}`; `GitCommandError → stream.finishSide(side) + {kind:"empty"}`; abort re-thrown; anything else re-thrown. File side pre-checks: `byteLength > MAX_FILE_BYTES` → markTooLarge BEFORE reading; sniff-detected assets over the cap → `{kind:"tooLarge", byteLength}` after read.

### Decisive source
```ts
if (signal?.aborted) throw error;
if (error instanceof git.GitOutputTruncatedError) {
	stream.markTooLarge(side);
	emit();
	return { kind: "tooLarge" };
}
if (error instanceof git.GitCommandError) {
	stream.finishSide(side);
	emit();
	return { kind: "empty" };
}
```

**Flow:** Truncation is a first-class state (`markTooLarge` completes the side so the differ can finish) rendered as a "too large" placeholder; command failure degrades to an EMPTY side so a deleted/unreadable revision still renders the surviving side; only cancellation propagates. The worktree-file path mirrors this: size check before any read, then binary/asset detection on the first `BINARY_SNIFF_BYTES` slice, with an emit-poll loop (`while (!done) { await Bun.sleep(4); emit(); }`) driving live progress while `openFile` reads natively.
**Invariant:** A per-side failure NEVER rejects `streamContents` unless it is an abort — the other side's content still streams and diffs; `markTooLarge` vs `finishSide` is the difference between a placeholder and an empty pane.
**Probe:** `grep -cF 'kind: "tooLarge"' packages/coding-agent/src/cli/git-tui/state.ts` → `6` and `grep -nF 'Bun.sleep(4)' packages/coding-agent/src/cli/git-tui/state.ts` → line `661`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "markTooLarge GitOutputTruncatedError tooLarge empty side streamContents", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder (abort > truncation→placeholder > command-error→empty > rethrow); adapt placeholder rendering; omit the LFS-missing variant if LFS is out of scope. Direct tests pin truncation at the generator layer (`git-show-stream.test.ts`); the UI ladder itself has no dedicated unit test (coverage caveat).
