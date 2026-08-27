<!-- capsule-v2 -->
# Results-instance binding — how do you keep per-instance derived data honest when results can be passed between instances?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** When a public API derives data from lint results using instance-private state (the config loader), how do you fail loudly on foreign results instead of silently returning wrong data?

## getRulesMetaForResults instance-binding guard + <text> normalization
**Path/Symbol:** `lib/eslint/eslint.js`: `getRulesMetaForResults` (:887–945), `createExtraneousResultsError` (:266–273), `createRulesMeta` (:103–108), `hasFlag` (:951–954); `lib/eslint/eslint-helpers.js:getPlaceholderPath` (:648–650, `join(cwd, "__placeholder__.js")`).
**Signature:** `getRulesMetaForResults(results: LintResult[]): Record<string, RulesMeta>`; throws `TypeError("Results object was not created from this ESLint instance.", { cause })`.
**Data Shape:** input `LintResult[]` (messages + suppressedMessages); output maps ruleId → rule.meta for every RESOLVABLE rule; `hasFlag(flag)` is a one-line delegation to `privateMembers.get(this).linter.hasFlag(flag)`.

### Decisive source
```js
// Normalize filename for <text>.
const filePath = result.filePath === "<text>" ? getPlaceholderPath(cwd) : result.filePath;
const allMessages = result.messages.concat(result.suppressedMessages);
for (const { ruleId } of allMessages) {
    if (!ruleId) continue;
    let configs;
    try {
        configs = configLoader.getCachedConfigArrayForFile(filePath);
    } catch (err) {
        throw createExtraneousResultsError(err);   // loader failure ⇒ foreign results
    }
    const config = configs.getConfig(filePath);
    if (!config) {
        throw createExtraneousResultsError();      // no config ⇒ foreign results
    }
    const rule = config.getRuleDefinition(ruleId);
    if (rule) resultRules.set(ruleId, rule);       // unknown rules silently skipped
}
return createRulesMeta(resultRules);
```

**Flow:** empty results short-circuit to `{}` → per result, swap `"<text>"` for the placeholder path so the loader resolves a REAL config → walk messages AND suppressedMessages → skip directive entries (no ruleId) → config-array lookup wrapped in try/catch (any loader error means the results came from another instance/cwd) → missing config likewise → collect resolvable rule definitions into a Map → project to `{ruleId: meta}`.
**Invariant:** results are bound to the producing INSTANCE — cross-instance use throws a TypeError with the original error as `cause`, never returns partial/wrong meta; `"<text>"` MUST be normalized before lookup or every lintText result would throw; unknown rules are silently dropped (the meta map is best-effort over resolvable rules, by design — a removed plugin must not break meta extraction).
**Probe:** `tests/lib/eslint/eslint.js` (:10639+ `describe("getRulesMetaForResults()")` — TypeError pinned at :10680/:10743/:10755 incl. "results created from a different instance"; :445 `describe("hasFlag")`). Live probes this pass: foreign-instance results (1 message, same cwd, different ESLint object) → `TypeError: Results object was not created from this ESLint instance.`; own-instance → `{ semi: <meta> }`; `lintText("var z = 9\n")` result with `filePath "<text>"` resolves the same meta via the placeholder; `[]` → `{}`. Mocha subset `--grep "getRulesMetaForResults|hasFlag"` → 38 passing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "getRulesMetaForResults createExtraneousResultsError getPlaceholderPath", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.eslint.eslint.ESLint.getRulesMetaForResults" });
```

## Verdict
Adopt the fail-loud instance-binding pattern for any API that derives data from opaque result objects using instance-private state: wrap the private lookup in try/catch and convert every failure mode (loader error, missing entry) into ONE typed "foreign results" error carrying the cause. Adapt the `<text>`-style placeholder normalization to your host's virtual-file convention; keep unknown-id silent-skip when downstream consumers must tolerate removed plugins. Caveat: Codebase Memory MCP was not connected in the mining session; anchors verified by direct byte-matched source reads at the git-clean pin.
