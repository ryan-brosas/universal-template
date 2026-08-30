<!-- capsule-v2 -->
# System-prompt mode injection — how does the loop keep the agent on-script every single turn?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** Which instructions are re-injected per turn, and how do they adapt to which session files exist?

## before_agent_start systemPrompt append — rules path, ideas nudge, checks doctrine, guardrail
**Path/Symbol:** `extensions/pi-autoresearch/index.ts:1007–1045`; constant `BENCHMARK_GUARDRAIL` :60–61 (server twin :87–88).
**Signature:** handler returns `{ systemPrompt: event.systemPrompt + extra }` ONLY when `runtime.autoresearchMode` — zero footprint when off.
**Data Shape:** existence probes drive three optional blocks: `autoresearch.md` (always referenced), `autoresearch.checks.sh` (checks block), `autoresearch.ideas.md` (backlog nudge).

### Decisive source
```ts
let extra =
  '\n\n## Autoresearch Mode (ACTIVE)' +
  '\nYou are in autoresearch mode. Optimize the primary metric through an autonomous experiment loop.' +
  '\nUse pi-autoresearch init, run, and log to manage experiments. NEVER STOP until interrupted.' +
  `\nExperiment rules: ${mdPath} — read this file at the start of every session. ...` +
  "\nWrite promising but deferred optimizations as bullet points to autoresearch.ideas.md — don't let good ideas get lost." +
  `\n${BENCHMARK_GUARDRAIL}` +
  '\nIf the user sends a follow-on message while an experiment is running, finish the current run + log cycle first, then address their message in the next iteration.';
```

**Flow:** every agent turn in mode → append guidance: never stop; read rules file each session (compaction summary carries them post-compact); park deferred ideas in the backlog file; when checks exist inject their full doctrine (auto-run after passing benchmarks, log `checks_failed`, keep impossible after failed checks, timing excluded from metric); prune stale ideas. The anti-overfit guardrail string is appended verbatim here AND to every kickoff/resume message.
**Invariant:** injection is conditional on the MODE FLAG, not on results — even a fresh pre-baseline session gets steering. The "finish run+log before user requests" rule resolves the priority conflict between human interruptions and loop atomicity WITHOUT dropping user input. All paths share ONE guardrail constant so wording can't drift between surfaces.
**Probe:** anchors: `grep -c BENCHMARK_GUARDRAIL extensions/pi-autoresearch/index.ts` → 6 lines (:60 def + kickoff :967/:968 + resume fns :533/:544 + prompt-injection :1025); `grep -rn 'NEVER STOP until interrupted' extensions/pi-autoresearch/index.ts skills/autoresearch-create/SKILL.md` → exactly 2 files; direct test support: regression.test pins duplicate-command guard feeding this same lifecycle.
**Retrieve:**
```bash
# BM25 noise-filter regression class (recurred 2026-08-24): multi-word queries on
# this small corpus can return total:0. The working primitive is search_code:
codebase-memory-mcp cli search_code --project "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness" --pattern 'BENCHMARK_GUARDRAIL'
# → 6 results incl. dispatchAction server.ts:717-1567 (:764), composeResumeMessage index.ts:529-535 (:533), composeCompactionResumeMessage :537-546 (:544)
```

## Verdict
Adopt per-turn conditional injection with file-existence-adaptive blocks and the shared anti-cheat constant; adapt instruction content to your domain; omit the pi ExtensionAPI return shape for other hosts. Coverage caveat: prompt text is source-pinned only (no test asserts its content).
