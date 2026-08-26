<!-- capsule-v2 -->
# bootstrap isolation rule — how does the global-state file stay a leaf of the import DAG?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** A god-singleton needs types and helpers from everywhere — how do you keep it importable from EVERYWHERE without creating cycles (and what's the escape hatch)?

## state.ts isolation discipline: type-only imports, duplicated types, lint-escapable rule
**Path/Symbol:** `src/bootstrap/state.ts`: eslint disable `:17`, crypto indirection comment `:13-16`, `SessionCronTask` local duplicate `:1280-1292` + rationale `:140-142`, `AttributedCounter` local type `:41-43`, import block `:1-29` (14 `import type` lines, 4 value imports).
**Signature:** Value imports allowed: `realpathSync` (node:fs), `sumBy` (lodash-es leaf), `cwd` (process), `randomUUID` (via `src/utils/crypto.js`). Everything else — `HookEvent`, `ModelUsage`, `AgentColorName`, `HookCallbackMatcher`, `SettingSource`, `PluginHookMatcher`, `SessionId`, `ModelSetting`, `ModelStrings`, SDK/OTel provider types — arrives as `import type`.
**Data Shape:** The custom lint rule name is the contract: `custom-rules/bootstrap-isolation`. Snapshot caveat: this public snapshot ships NO eslint/biome config (`package.json` has no lint script or linter dep), so the rule is enforced upstream — porters adopting the pattern must bring their own equivalent rule. The disable comments still mark every sanctioned exception site in-source.

### Decisive source
```ts
// :13-18
// Indirection for browser-sdk build (package.json "browser" field swaps
// crypto.ts for crypto.browser.ts). Pure leaf re-export of node:crypto —
// zero circular-dep risk. Path-alias import bypasses bootstrap-isolation
// (rule only checks ./ and / prefixes); explicit disable documents intent.
// eslint-disable-next-line custom-rules/bootstrap-isolation
import { randomUUID } from 'src/utils/crypto.js'
// :140-142 (why SessionCronTask is defined locally)
// SessionCronTask below (not importing from cronTasks.ts keeps
// bootstrap a leaf of the import DAG).
```

**Flow:** any module may import state.ts because state.ts imports (almost) nothing → runtime values restricted to true leaves (fs, lodash subpath, process, a pure crypto re-export) → cross-cutting types imported TYPE-only so they erase at compile time → when a type would drag a heavy module in, DUPLICATE its shape locally instead → the rare genuine exception takes an aliased path (`src/utils/crypto.js` bypasses the ./-prefix check) WITH an explicit eslint-disable documenting intent.
**Invariant:** Cycle-freedom for a singleton is enforced at the IMPORTS side, not the consumers: if nothing here pulls real modules, everyone can depend on it. Type-only imports are the primary tool; local type duplication (`SessionCronTask`, `ChannelEntry`, `InvokedSkillInfo`, `RegisteredHookMatcher`) is the fallback with the trade-off written down. Escape hatches must be LOUD (inline disable + comment explaining why the alias dodge works) so the rule stays auditable. The same discipline shows in accessor design: no lazy requires, no side effects beyond one `getInitialState()` at module load.
**Probe:** Deterministic pins: `grep -n 'custom-rules/bootstrap-isolation' src/bootstrap/state.ts` → `17:`; `grep -c '^import type' src/bootstrap/state.ts` → `14`; `grep -n 'keeps$' src/bootstrap/state.ts | head -1` → `142:` (comment tail "bootstrap a leaf of the import DAG"); `grep -n 'rule only checks' src/bootstrap/state.ts` → `15:`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "bootstrap isolation import DAG leaf state", limit: 10 });
```

## Verdict
Adopt import-side cycle defense for shared singletons: type-only imports, local duplicates of volatile types, loud documented escapes via a custom lint rule. Adapt rule mechanics to your linter. Omit the browser-build crypto indirection unless you ship dual runtimes.
