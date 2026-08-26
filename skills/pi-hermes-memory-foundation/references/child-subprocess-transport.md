<!-- capsule-v2 -->
# Child `pi -p` subprocess transport — temp-file prompt, file-sentinel cancellation, watchdog tree-kill, override-failure retry

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How do you run a one-shot LLM task in a CLI child process — passing a multi-kilobyte prompt safely, honoring an AbortSignal across process boundaries, killing the whole child tree on timeout, and surviving a bad model override?

## execChildPrompt + resolveWatchedChildPiInvocation
**Path/Symbol:** `src/handlers/pi-child-process.ts:execChildPrompt` (:397–456), `buildChildPiPromptArgs` (:242–257), `resolveChildPiInvocation` (:332–353), `resolveWatchedChildPiInvocation` (:355–370), `writePromptToTemporaryFile` (:385–395), retry predicates (:51–52, :372–383); watchdog asset `src/handlers/child-process-watchdog.mjs` (90 L).
**Signature:** `execChildPrompt(pi, prompt, config, { signal?, timeoutMs, retryWithoutOverrides? }) → PiExecResult { code, stdout?, stderr?, killed? }`.
**Data Shape:** prompt travels as an `@/abs/path/prompt.md` file reference (mode 0o600 in a `pi-hermes-prompt-*` mkdtemp dir); a sibling empty `cancel` file is the cross-process cancel sentinel; argv shape: `-p --no-session [--model M] [--thinking T] --no-extensions -e <ext>… @prompt.md`.

### Decisive source
```ts
const execOptions = { timeout: options.timeoutMs + WATCHDOG_EXIT_GRACE_MS };   // 5 s grace AFTER
const temporaryPrompt = await writePromptToTemporaryFile(prompt);              // the watchdog fires
const cancellationPath = join(temporaryPrompt.dir, "cancel");
const requestCancellation = () => {
  void fs.writeFile(cancellationPath, "", { mode: 0o600 }).catch(() => {});    // FILE = IPC channel
};
options.signal?.addEventListener("abort", requestCancellation, { once: true });
if (options.signal?.aborted) requestCancellation();   // pre-aborted signals still request cancel

// … invocation wrapped by the watchdog:
//   node child-process-watchdog.mjs <timeoutMs> <cancelPath> pi -p …
// watchdog: spawn detached → poll existsSync(cancelPath) → on timeout/cancel
//           signalTree("SIGTERM") then SIGKILL after 500 ms; process.kill(-pid)
//           hits the whole DETACHED GROUP (taskkill /T /F on Windows)

try {
  const result = await pi.exec(invocation.command, invocation.args, execOptions);
  if (result.code === 0 || !options.retryWithoutOverrides || !hasChildLlmOverrides(config)
      || !shouldRetryWithoutOverrides(result)) return result;
} catch (error) {
  if (!options.retryWithoutOverrides || !hasChildLlmOverrides(config)
      || !shouldRetryWithoutOverridesForError(error)) throw error;
}
return await pi.exec(retryInvocation.command, retryInvocation.args, execOptions);
// finally: removeEventListener + rm tempdir (fallback: unlink just the prompt file)
```

Retry text gate (`shouldRetryWithoutOverridesFromText`): stderr/stdout must match BOTH `/\b(model|provider|thinking)\b/i` AND `/\b(not found|unknown|invalid|unsupported|unavailable|unrecognized|no match|no matches|cannot resolve|failed to resolve)\b/i` — i.e. "the configured override itself is wrong", not any failure.
**Flow:** (1) prompt written to a 0o600 temp file (avoids ARG_MAX and shell-quoting hazards of inline prompts); (2) abort wiring converts the in-process AbortSignal into filesystem IPC the watchdog can see; (3) the watchdog owns timeout + tree termination so a hung `pi` cannot outlive its budget; (4) a failed run that looks like a bad model/thinking override retries ONCE with overrides stripped (`basePromptArgs` drops them); (5) tempdir cleanup runs even when the exec throws.
**Invariant:** the parent's own exec timeout must EXCEED the watchdog's (grace 5 s) or the watchdog's cleanup never gets to run; cancellation is best-effort signaling (write failures swallowed) because the watchdog's hard timer is the real enforcement. Windows needs direct-cli resolution (`resolveChildPiInvocation`) since `.cmd` shims break detached-group kills.
**Probe:** `tests/handlers/pi-child-process.test.ts` — asserts temp-prompt arg construction, retry-without-overrides triggered by matching stderr text and NOT by unrelated failures, cancel-sentinel creation on already-aborted signals, and watchdog argv shape (`timeout`, `cancelPath`, real command). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "execChildPrompt resolveWatchedChildPiInvocation buildChildPiPromptArgs", limit: 5 })`

## Verdict
Adopt the transport whenever a host must delegate one-shot LLM work to a CLI child with proper cancellation. Adapt CLI name/flags, grace period, and the override-retry regexes to the target binary. The legacy-surface ruling in this leaf's Boundaries is hereby NARROWED to the deprecated `inheritedExtensionArgs` helper only.
