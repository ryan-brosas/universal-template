<!-- capsule-v2 -->
# Goal & preference extractors — goal substantiation filters, template truncation, scope-change capture, preference dedup

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you separate the user's actual goals from pasted output, command templates, and chatter in user messages?

## Goals: first-block seed + scope-change tracking
**Path/Symbol:** `src/compaction/extract/goals.ts:47-79` (`extractGoals`); guards :11-27 (`NOISE_SHORT_RE`, `NON_GOAL_RE`, `TEMPLATE_SIGNAL_RE`).
**Signature:** `extractGoals(blocks): string[]` (max 8; first block seeds up to 6 lines; scope changes append ≤3 lines under a literal `[Scope change]` header).
**Data Shape:** `MAX_GOAL_CHARS = 200`; substantiation = length >5, ≤200, not noise-short, not NON_GOAL (table borders, code fences, code lines, URLs, `\n` literals, issue-command templates).

### Decisive source
```ts
    const leading = b.text.slice(0, LEADING_CHARS);   // LEADING_CHARS = 200
    if (SCOPE_CHANGE_RE.test(leading)) {
      latestScopeChange = lines.slice(0, 3).map((l) => clip(l, MAX_GOAL_CHARS));
    } else if (TASK_RE.test(leading) && lines[0].length > 15) {
      latestScopeChange = lines.slice(0, 2).map((l) => clip(l, MAX_GOAL_CHARS));
    }
  }
  // Only emit the [Scope change] marker when we actually captured bullets.
  if (latestScopeChange && latestScopeChange.length > 0) {
    goals.push('[Scope change]', ...latestScopeChange);
  }
```
Template truncation (:24-27) cuts a user block at the FIRST line matching `For each…|Do NOT implement…|Analyze and propose…|If Task/context…|Output:$` — the rest of such messages is boilerplate, not intent. Scope/task regexes test only the LEADING 200 chars so pasted output below the instruction cannot trigger matches.

**Preferences:** `src/compaction/extract/preferences.ts:14-42` — six tightened patterns (`prefer*`, `don't want`, `always use/do/...`, `never push/commit/...`, `please use/avoid/...`, `style|format|language|naming:`), questions rejected (`endsWith('?')`), **one preference per user block**, max 10 overall; `dedupPreferencesAgainstGoals` removes case-insensitive overlaps so the two prompt sections stay disjoint.

**Flow:** blocks → per-user-block filter/truncate → seed from first substantive block → later blocks update only the pending scope-change slot → emit once at end. Preferences run as an independent pass then dedupe against goals.
**Invariant:** Goals are append-only via the single `[Scope change]` slot — mid-conversation pivots never overwrite the original goal section, they annotate it. The leading-chars restriction is load-bearing: testing full text would classify pasted logs as new tasks.
**Probe:** `grep -c "SCOPE_CHANGE_RE" src/compaction/extract/goals.ts` → 2; `grep -c "TEMPLATE_SIGNAL_RE" src/compaction/extract/goals.ts` → 2; `grep -c "\[Scope change\]" src/compaction/extract/goals.ts` → 2 (comment + emission). Direct tests: `tests/full-fidelity-snapshot.test.ts:160` "extracts goals from user messages".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractGoals scope change template signal user", limit: 10 });
```

## Verdict
Adopt substantiation-first goal mining with leading-window intent tests and one-slot scope-change annotation. Adapt regex vocabularies (SCOPE_CHANGE_RE carries pivot phrases like `instead|actually|change of plan|pivot`) and preference patterns to your users' phrasing. Omit the per-block preference cap at your peril — rule-list pasting otherwise floods the section.
