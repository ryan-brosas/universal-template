<!-- capsule-v2 -->
# Shell alias & CLI resolution — how does the CLI become available to every bash tool-call the agent makes?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How is the wrapper installed and how are dist-vs-source entrypoints resolved?

## Write-once-differs wrapper + dist-first CLI resolution
**Path/Symbol:** `extension/harness.ts:installShellAlias` (:72-101), `resolveCli` (:45-55), `getDistCliPath` (:12-21); `harness/cli.ts:resolveProjectRoot` (:301-312).
**Signature:** `installShellAlias(): void`; `resolveCli(): {command, prefixArgs, cliPath, cwd}`.
**Data Shape:** wrapper at `~/.pi/agent/bin/pi-messenger-swarm`, `#!/bin/sh\ncd "<cwd>"\nexec <cmd>[ prefix] "<cli>" "$@"`, mode 0o755.

### Decisive source
```ts
// Only write if content differs (avoids unnecessary writes on every session_start)
let currentContent: string | null = null;
try { currentContent = fs.readFileSync(linkPath, 'utf-8'); } catch {}
if (currentContent !== wrapperContent) {
  fs.writeFileSync(linkPath, wrapperContent, { mode: 0o755 });
}
```
```ts
export function resolveCli(): CliResolution {
  const distCli = getDistCliPath();          // dist/harness/cli.js when running from npm package
  if (distCli) return { command: 'node', prefixArgs: [], cliPath: distCli, cwd: join(__dirname, '..') };
  return { command: 'npx', prefixArgs: ['tsx'], cliPath: sourceCli, cwd: projectRoot };
}
```

**Flow:** at every session_start the extension regenerates the wrapper text from resolved CLI paths and writes it only on content change; pi prepends `~/.pi/agent/bin` to PATH for child bash processes, so model tool-calls can invoke `pi-messenger-swarm` directly. Project-root resolution walks up ≤20 levels looking for `.git/` or `.pi/` so subdirectory invocations still find the right `.pi/messenger`.
**Invariant:** Wrapper-not-symlink is deliberate: the CLI's location differs between tsx-source and compiled-dist installs, and a symlink would strand one mode. Content-compare avoids mtime churn on every session start. The `.git-or-.pi` ancestor walk bounds at 20 levels then falls back to start dir.
**Probe:** direct test coverage via harness suites (`tests/swarm/soft-restart.test.ts` exercises CLI/server interplay); `grep -c "currentContent !== wrapperContent" extension/harness.ts` (=1); `grep -n "0o755" extension/harness.ts`; `grep -c "\.git'\) || fs.existsSync(path.join(dir, '\.pi')" harness/cli.ts` (=1 — use fixed-string grep `-F ".git") ||`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "installShellAlias resolveCli getDistCliPath resolveProjectRoot", limit: 5 });
```

## Verdict
Adopt diff-gated PATH-dir wrapper installation and dist-first resolution; adapt bin dir to your host's PATH injection mechanism; keep an explicit ancestor-walk cap.
