<!-- capsule-v2 -->
# Detached Chrome launcher & targeted kill — how does a launcher's Chrome outlive the process that started it, and how do you kill ONLY that instance?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Why does a Bun/Node-spawned CDP Chrome die on Windows the moment the setup script exits, and how do you reset one platform's browser without touching the user's own Chrome?

## Host-aware detach (Job Object escape) + profile-scoped kill
**Path/Symbol:** `scripts/lib/host.ts`:`launchChromeDetached`, `windowsStartProcessCommand`, `killChromeForProfile`, `resolveChromeBinary`, `defaultWorkProfile` (`:65-184`).
**Signature:** `launchChromeDetached(chromeBin: string, args: string[], host?: HostOS): void`; `windowsStartProcessCommand(chromeBin: string, args: string[]): string` (pure); `killChromeForProfile(workProfile: string, host?): Promise<void>`.
**Data Shape:** `HostOS = 'windows' | 'macos' | 'linux'`. Work profile is a STABLE per-user dir (`%LOCALAPPDATA%\locoagent-chrome-profile` / `~/Library/Application Support/locoagent-chrome-profile` / `$XDG_DATA_HOME|~/.local/share/locoagent-chrome-profile`) — deliberately NOT under temp so logins survive reboot and temp-cleaners.

### Decisive source
```ts
if (host === 'windows') {
  // Bun assigns spawned children to a Job Object killed when the launcher exits;
  // Start-Process creates a process OUTSIDE our job, so the CDP Chrome persists.
  Bun.spawnSync(['powershell', '-NoProfile', '-Command',
    windowsStartProcessCommand(chromeBin, args)], { stdout: 'ignore', stderr: 'ignore' })
  return
}
const child = Bun.spawn([chromeBin, ...args], { stdout:'ignore', stderr:'ignore', stdin:'ignore' })
child.unref()   // POSIX: detached spawn + unref survives parent exit
```
and the scoped kill:
```ts
// pkill -f matches the full argv; the unique user-data-dir path scopes it.
Bun.spawnSync(['pkill', '-f', `--user-data-dir=${workProfile}`], {...})
```

**Flow:** resolve binary (explicit `CHROME_BIN` if it exists → first existing host candidate → throw with "set CHROME_BIN") → launch fully detached per host → for resets, match Chrome processes by their `--user-data-dir=<profile>` argv fragment (CIM query filtering `chrome.exe` CommandLine on Windows; `pkill -f` elsewhere) and kill only those. `windowsStartProcessCommand` PS-single-quotes every arg and additionally double-quotes any `--key=value` whose value contains spaces so Start-Process doesn't re-split a profile path through a spaced username.
**Invariant:** The isolated work profile is never the user's real Chrome profile; kills are always scoped by that exact path ("never touches the user's normal Chrome"). A plain detached+unref is INSUFFICIENT on Windows — this is the exact bug class the PowerShell path exists for.
**Probe:** `scripts/lib/host.test.ts` — `defaultWorkProfile lives under a stable per-user dir, not temp` (:34, asserts XDG override AND not-contains-Temp), `resolveChromeBinary returns an existing explicit path` (:51), `windowsStartProcessCommand single-quotes the binary and each arg` (:62), `windowsStartProcessCommand double-quotes a --key=value whose value has spaces` (:73).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "launchChromeDetached windowsStartProcessCommand killChromeForProfile", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the Job-Object-escape detach on Windows, pure command builder with space-safe quoting, profile-scoped kill, and the stable-not-temp work-profile rule. Adapt binary candidate lists and profile dir names to your product. Omit the specific CIM/pkill syntax only if your host layer has an equivalent scoped matcher — never fall back to kill-all-chrome.
