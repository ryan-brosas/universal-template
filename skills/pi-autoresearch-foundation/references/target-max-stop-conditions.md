<!-- capsule-v2 -->
# Target/max stop conditions — how does an autonomous loop end itself without a human?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** Where are the two self-stop conditions evaluated, and why is the run-side check a pre-guard while the target check rides the log?

## maxExperiments pre-block + limitReached/targetReached post-log ladders
**Path/Symbol:** `harness/server.ts` — run pre-guard :917–923; log tail `limitReached` :1452–1457, `targetReached` :1459–1471; both flip `session.autoresearchMode = false`.
**Signature:** guard: `state.maxExperiments !== null && state.results.length >= state.maxExperiments ⇒ refuse to run`; target: `status==='keep' && targetValue!==null && metric>0 && (lower ? metric<=targetValue : metric>=targetValue)`.
**Data Shape:** both thresholds arrive via init params (`--max-experiments`, `--target-value`) and persist in the config header.

### Decisive source
```ts
if (limitReached) {
  text += `\n\n🛑 Maximum experiments reached (${state.maxExperiments}). STOP the experiment loop now.`;
  session.autoresearchMode = false;
}
if (targetReached) {
  text += `\n\n🎯 TARGET REACHED! ${state.metricName} = ${formatNum(metric, state.metricUnit)} ...`;
  text += `\n✅ Optimization complete. STOP the experiment loop now.`;
  session.autoresearchMode = false;
}
```

**Flow:** run action checks the cap BEFORE any side effect (no benchmark fires past the budget). After each log: cap check counts ALL results (any status); target check requires a KEPT positive metric that crosses the threshold by direction. Either ⇒ mode flag off server-side AND imperative "STOP now" text; the extension's per-turn resume gate (`shouldAutoResumeAfterTurn` reads `runtime.autoresearchMode`, mirrored off via deactivate/clear paths) then never re-arms.
**Invariant:** stopping is two-channel BY DESIGN — the machine flag (server session + extension runtime) halts automation, while the textual command tells the LLM agent to stop prompting new runs (belt-and-suspenders because the agent could otherwise call run again immediately). Target only ever triggers on keep: a discarded lucky number must not end the optimization. Status widget mirrors progress (`🎯 … ✓` when displayVal crosses).
**Probe:** anchors: `grep -n 'maxExperiments !== null' harness/server.ts` → exactly :918 (pre-guard) + :1359 (text) + :1453 (limitReached); `grep -n 'TARGET REACHED' harness/server.ts` → exactly :1468; direct test support: utils.test 'isBetter' cases pin direction math used by the predicate.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "targetValue maxExperiments TARGET REACHED autoresearchMode false", limit: 10 });
```

## Verdict
Adopt the dual-channel stop (flag + imperative text) and keep-only targeting verbatim; adapt thresholds/wording; omit nothing — dropping either channel regresses to a loop that only a human can kill. Coverage caveat: stop ladder untested directly — source-pinned.
