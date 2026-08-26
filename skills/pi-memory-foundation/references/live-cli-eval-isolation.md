<!-- capsule-v2 -->
# Live-CLI eval isolation — how do you run a real agent CLI against your extension without destroying (or leaking) the developer's own memory?

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory` (full mode 380n/941e @2026-08-22T23:46:09Z). **Question:** How do e2e/eval scripts drive the production `pi` CLI + real `~/.pi/agent/memory` safely — event parsing, failure diagnostics, and backup/restore around the live memory dir?

## Live-CLI eval isolation
**Path/Symbol:** `test/eval-recall.ts` (`runPi` :336–385, `backupFile` :387–391, `restoreFile` :393–405; corpus seeding `seedCorpus` :407–425); twin implementation in `test/e2e.ts` (`runPi` :106–165, `formatPiFailure` :167–176, `assertPiExitedOk` :178–181, `backupFile` :183–188, `restoreFile` :190–199).
**Signature:** ``runPi(prompt): PiResult`` = ``execSync(`echo "${b64}" | base64 -d | pi -p --mode json [-e EXTENSION_PATH] --no-session`, { timeout: 120_000, maxBuffer: 10MB })``.
**Data Shape:** `PiResult = { exitCode, stdout, textOutput, events[], toolCalls[] }`; NDJSON lines parsed leniently (non-JSON lines skipped), assistant text accumulated from `message_end` events, tool usage from `tool_execution_start.toolName`.

### Decisive source
```ts
// base64 pipe transport: prompt NEVER touches the shell as raw text
const cmd =
  `echo "${promptB64}" | base64 -d | ` +
  `pi -p --mode json${providerArg}${modelArg} -e "${EXTENSION_PATH}" --no-session`;
...
} catch (err: any) {          // execSync throws on nonzero exit — salvage partial output
  stdout = err.stdout ?? "";   // timeout/crash still yields parsed events
  exitCode = err.status ?? 1;
}
// restoreFile: restore-if-backup ELSE delete-if-exists — seeded files vanish on cleanup,
// pre-existing files come back byte-identical
function restoreFile(filePath: string) {
  const backup = filePath + BACKUP_SUFFIX;
  if (fs.existsSync(backup)) { fs.copyFileSync(backup, filePath); fs.unlinkSync(backup); }
  else if (fs.existsSync(filePath)) { fs.unlinkSync(filePath); }
}
```

**Flow:** preflight round-trip → `try { seed → qmd update → timed runs } finally { restore }`. Backups are taken for MEMORY.md, SCRATCHPAD.md and every daily file the corpus will touch BEFORE any write.
**Invariant:** every live-agent run must be wrapped so that a timeout or crash still returns partial stdout (assertions then fail with evidence, not with a lost 120-second hang); cleanup must distinguish "file existed before" from "file created by the test" — never `rmSync` a directory you don't own. Prompts travel base64-encoded through stdin because shell-quoting arbitrary prompts is unfixable at the margin.
**Probe:** `test/unit.test.ts` is the zero-dependency tier (182 pass / 0 fail EXECUTED pass 1 via `bun test`, scratch clone); this live tier requires `pi` + API key (+ `qmd` for search arms) — runner-blocked in this environment, recorded per-capsule.
**Coverage caveat:** live-CLI paths verified by source read + graph retrieval only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "runPi execSync message_end tool_execution_start backupFile", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the b64-stdin pipe, the throw-salvage exec wrapper, the `.suffix` backup + restore-or-delete protocol, and the two-tier test strategy (mock-API unit tier / live-CLI eval tier). Adapt timeouts, maxBuffer, and file layout to your host agent. Omit the provider/model pinning flags unless your CLI supports them.
---
