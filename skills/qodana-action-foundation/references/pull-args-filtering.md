<!-- capsule-v2 -->
# Pull-args filtering — why does `qodana pull` receive only a four-flag subset of the scan args?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** The user wrote one `args` string — how does the pre-flight image pull decide which flags apply to it?

## extractArg whitelist over -l/--image/-i/--config
**Path/Symbol:** `common/qodana.ts:extractArg` (:158-171), `getQodanaPullArgs` (:206-227), `isPullSkipped` (:186-188); call sites `scan/src/utils.ts:prepareAgent` (:344-361), `vsts/src/utils.ts:prepareAgent` (:183-199); GitLab has NO pull step (its native-mode injection replaces it).
**Signature:** `extractArg(argShort: string, argLong: string, args: string[]): string`; `getQodanaPullArgs(args): string[]`.
**Data Shape:** Output is one of `['pull']` plus up to four flag/value pairs, in fixed order linter→image→project→config.

### Decisive source
```ts
export function getQodanaPullArgs(args: string[]): string[] {
  const pullArgs = ['pull']
  const linter = extractArg('-l', '--linter', args)
  if (linter) pullArgs.push('-l', linter)
  const image = extractArg('--image', '--image', args)
  if (image) pullArgs.push('--image', image)
  const project = extractArg('-i', '--project-dir', args)
  if (project) pullArgs.push('-i', project)
  const config = extractArg('--config', '--config', args)
  if (config) pullArgs.push('--config', config)
  return pullArgs
}
```

**Flow:** scan args are already tokenized → linear scan for each whitelisted flag (short OR long form), taking the NEXT token as its value (first occurrence wins, break after match) → build the pull command from found pairs only. prepareAgent runs pull ONLY when NOT native mode AND NOT --skip-pull; nonzero pull exit fails the job early (`core.setFailed('qodana pull failed…')`) before wasting a full analysis on a missing image.
**Invariant:** Pull must NEVER receive arbitrary user flags (analysis-only flags like --fail-threshold would be rejected or misinterpreted by the pull verb) — the whitelist IS the contract. extractArg's first-match + adjacent-token semantics mean `--linter=x` (equals-form) is INVISIBLE to it; porters relying on equals-form flags silently lose their image pin.
**Probe:** no direct test for getQodanaPullArgs (coverage caveat recorded); behavior pinned by range :206-227 and by symmetry with the tested `getQodanaScanArgs` fixture (scan/__tests__/main.test.ts :85-93). Graph probe: search_graph "extractArg pull" resolves both functions line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "getQodanaPullArgs extractArg linter image", limit: 6 });
```

## Verdict
Adopt whitelist-subset extraction whenever one CLI verb pre-stages for another; adapt the flag set to your tool's pre-stage surface; document the equals-form blind spot in your own port.
