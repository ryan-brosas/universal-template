<!-- capsule-v2 -->
# Agent-browser shell bridge — how do you drive a CDP browser from a Node/Bun workflow and run arbitrary JS without shell-quoting pain?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the `ab` / `abEval` pair that every executor uses to issue agent-browser commands and evaluate JS against the pinned CDP session?

## Load the matching source dump
**Path/Symbol:** `workflows/executors/x-search-reply.ts`: `ab` (`:120-132`), `abEval` (`:134-152`), session flag (`:45`). Same pair in `hf-daily-papers.ts` (`ab` :55-67, `abEval` :69-91), `hf-papers-to-x.ts`, `linkedin-search-reply.ts`, `post-hf-paper.ts`.
**Signature:** `ab(cmd): string` = `execSync('agent-browser --cdp <port><sessionFlag> ' + cmd, { timeout: 30000, cwd: ROOT })`; `abEval(js, tmpDir): string` writes JS to `tmpDir/.eval-tmp.js` then runs `agent-browser ... eval "$(cat '<tmpJs>')"`.
**Data Shape:** `sessionFlag = config.platform && config.platform !== 'x' ? ' --session ' + config.platform : ''` (X is the default session, so no flag; other platforms get a named session). `abEval` returns the eval output with surrounding quotes JSON-unwrapped.

### Decisive source
```ts
function ab(cmd: string): string {
  try {
    return execSync(`agent-browser --cdp ${config.cdpPort}${sessionFlag} ${cmd}`,
      { encoding: 'utf-8', timeout: 30000, cwd: ROOT }).trim()
  } catch (e: any) { console.error(`[ab] Failed: ${cmd}`); return '' }
}
function abEval(js: string, tmpDir: string): string {
  if (!existsSync(tmpDir)) mkdirSync(tmpDir, { recursive: true })
  const tmpJs = resolve(tmpDir, '.eval-tmp.js'); writeFileSync(tmpJs, js, 'utf-8')
  try {
    let result = execSync(`agent-browser --cdp ${config.cdpPort}${sessionFlag} eval "$(cat '${tmpJs}')"`,
      { encoding: 'utf-8', timeout: 30000, cwd: ROOT }).trim()
    if (result.startsWith('"') && result.endsWith('"')) { try { result = JSON.parse(result) as string } catch (_) {} }
    return result
  } catch (e: any) { console.error(`[abEval] Failed`); return '' }
}
```

**Flow:** every browser command goes through `ab`, which shells `agent-browser --cdp <port>` (plus the platform session flag) with a 30 s timeout and swallows errors into `''` + a stderr log. Arbitrary JS goes through `abEval`, which writes the script to a temp file and shells it via `eval "$(cat ...)"` — sidestepping quote-escaping hell — then unwraps the quoted string the CLI returns so the result is JSON-parseable.
**Invariant:** The CDP port is pinned per-executor from config, and the platform session flag is derived once so X (the default) needs no flag while other platforms get an isolated named session. `ab` returns `''` on failure rather than throwing, so callers must treat empty-string as "couldn't do it" (they do — e.g. `if (!articleSnap)`). `abEval`'s temp-file indirection is the whole point: inline shell-quoting of multi-line JS is fragile, so the script is written to disk and `cat`-ed in. The eval output is JSON-unwrapped so the caller can `JSON.parse` it directly.
**Probe:** No direct test for these executors (coverage caveat — source-grounded). Deterministic probes: grep pins `agent-browser --cdp` at `x-search-reply.ts:122` and the `eval "$(cat '${tmpJs}')"` at `:140`; `grep -c 'eval-tmp' workflows/executors/*.ts` = 5 (present in every executor — repo-wide convention); `search_graph --name-pattern "findRef"` resolves it in x-search-reply, hf-papers-to-x, and post-hf-paper.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "agent-browser cdp eval abEval sessionFlag", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the `ab`/`abEval` shell-bridge pair (error-swallowing command wrapper + temp-file eval with quote-unwrap) for any Node/Bun workflow driving a CDP browser CLI. Adapt the CLI name, port source, and session-flag rule. Omit nothing — dropping the temp-file indirection reintroduces the shell-quoting fragility `abEval` exists to avoid.
