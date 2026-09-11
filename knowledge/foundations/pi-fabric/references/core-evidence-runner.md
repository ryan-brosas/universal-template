<!-- capsule-v2 -->
# Evidence runner — how do you run a shell command as verification evidence with a bounded, hash-covered output record and a kill that actually kills?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how is untrusted shell evidence executed so the result proves what happened (digest of FULL output) while storing only a bounded prefix, and how are timeouts enforced against process groups?

## Prefix-retained, wholly-hashed, group-killed command execution
**Path/Symbol:** `src/state/evidence-runner.ts:runCommand` (:99-207), `truncateUtf8` (:26-36), `terminateProcessTree` (:78-93), `collect` (:114-125).
**Signature:** `runCommand(command: string, options: {cwd; timeoutMs; signal?}): Promise<CommandResult>` where `CommandResult = {status: "confirmed"|"violated"|"error"; exitCode: number|null; output; outputBytes; outputOmittedBytes; outputDigest: "sha256:<hex>"; error?}`.
**Data Shape:** retained prefix cap `COMMAND_OUTPUT_MAX_BYTES = 32*1024`; hash + byte count cover the COMPLETE stdout+stderr stream; UTF-8 truncation backs off to whole bytes `(b & 0xc0) === 0x80`.

### Decisive source
```ts
const collect = (chunk) => {
  const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
  outputBytes += bytes.length;
  outputHash.update(bytes);                       // digest sees EVERYTHING
  if (retainedBytes >= COMMAND_OUTPUT_MAX_BYTES) return;
  const retained = bytes.subarray(0, Math.min(bytes.length, COMMAND_OUTPUT_MAX_BYTES - retainedBytes));
  outputChunks.push(retained); retainedBytes += retained.length;
};
...
child = spawn(command, { shell: true, cwd, detached: process.platform !== "win32" });
// POSIX shells lead DETACHED PROCESS GROUPS so timeout/abort can kill the group:
process.kill(-child.pid, "SIGKILL")   // fallback child.kill("SIGKILL")
// Windows: bounded taskkill /T /F tree cleanup (1s cap), then stream-destroy fallback.
...
finish(exitCode === 0 ? "confirmed" : "violated", exitCode);
```

**Flow:** spawn under the shell in its own process group → both streams feed `collect` which counts and hashes all bytes but retains only the first 32KB → timeout or abort triggers exactly one `terminate(reason)` (single-settled guard) which kills the group and, on Windows, waits for tree cleanup before resolving → close handler awaits termination, maps exit 0→`confirmed`, nonzero→`violated`, signal/timeout/abort→`error` with the reason — never throws.
**Invariant:** the evidence record must be verifiable after the fact (`outputDigest` over full output even when `outputOmittedBytes > 0`) and the process tree must not survive the caller's timeout; status mapping is total (no rejection path), so verification pipelines can treat any outcome as data. Truncation never splits a UTF-8 sequence.
**Probe:** `tests/state-provider.test.ts:164` ("verifies evidence: echo is confirmed, exit 1 is violated, and publishes state.violated"), `:244` ("fails closed on spawn errors, timeouts, and cancellation"), `:477` ("bounds huge failing output … 350000 chars"), `:306/:341` (certificate revocation on later failure / durable revocation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "runCommand CommandResult outputDigest terminateProcessTree truncateUtf8 confirmed violated", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt hash-everything/retain-prefix evidence records, process-group kill with Windows taskkill fallback, and total outcome mapping; adapt caps/status vocabulary; omit state-store certificate specifics (separate seam).
