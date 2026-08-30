<!-- capsule-v2 -->
# autoresearch.sh run-lock — why must the loop only ever execute its own benchmark script?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** How is an arbitrary-command escape blocked once the session has a benchmark script, without breaking env-var/wrapper prefixes?

## isAutoresearchShCommand — strip-prefix ladder then anchored single-command check
**Path/Symbol:** `extensions/pi-autoresearch/src/utils/validate.ts:13–30` + server copy `harness/server.ts:200–211` (guard call-site :948–955).
**Signature:** `isAutoresearchShCommand(command: string): boolean`; guard fires only when `autoresearch.sh` EXISTS in workDir.
**Data Shape:** input raw command string possibly prefixed by `VAR=value` assignments and `env|time|nice|nohup [flags] [n]` wrappers.

### Decisive source
```ts
cmd = cmd.replace(/^(?:\w+=\S*\s+)+/, "");            // FOO=bar BAZ=qux ...
do {
  prev = cmd;
  cmd = cmd.replace(/^(?:env|time|nice|nohup)(?:\s+-\S+(?:\s+\d+)?)*\s+/, "");
} while (cmd !== prev);                                // repeat until fixpoint (time nice nohup ...)
return /^(?:(?:bash|sh|source)\s+(?:-\w+\s+)*)?(?:\.\/|\/[\w/.-]*\/)?autoresearch\.sh(?:\s|$)/.test(cmd);
```

**Flow:** run action → if `autoresearch.sh` exists AND command fails this predicate ⇒ REJECT with explicit guidance text ("you must run it instead of a custom command … Use: pi-autoresearch run \"bash autoresearch.sh\""). Accept paths: bare/`./`/absolute autoresearch.sh; optional bash/sh/source with flags first; optional env-var and wrapper prefixes stripped before matching. Rejects: chained commands (`evil.py; autoresearch.sh` — script not FIRST real command), arguments-before-name forms (`cat autoresearch.sh`, `echo autoresearch.sh`), suffix look-alikes (`autoresearch.sh.bak`, `my-autoresearch.sh`).
**Invariant:** the anchor `(?:\s|$)` after the filename is what kills `.sh.bak` look-alikes; the fixpoint wrapper-strip loop is what keeps `time nice nohup ./autoresearch.sh` legal while `x.sh && autoresearch.sh` stays illegal (nothing strips the first command). Deliberate policy: the agent may benchmark ONLY through the reviewed script — arbitrary commands would let the loop drift into self-measured, non-comparable runs.
**Probe:** direct test `__tests__/unit/utils.test.ts:420–483` describe('isAutoresearchShCommand') — 11 its pin accepts (direct/bash/sh/source/flags/env/time-nice-nohup/complex combo) and rejects (chains, non-primary args, filename look-alikes, empty, unrelated commands); anchors `grep -c isAutoresearchShCommand` per file: validate.ts 1, utils.test.ts 33, harness/server.ts 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "isAutoresearchShCommand autoresearch.sh exists custom command", limit: 10 });
```

## Verdict
Adopt the predicate byte-for-byte (it is security-adjacent: it constrains what the autonomous agent may execute); adapt the filename/prefix list to your own script convention; omit nothing. Fully direct-tested — port the test file alongside.
