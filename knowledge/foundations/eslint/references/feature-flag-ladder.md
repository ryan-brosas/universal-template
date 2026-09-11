<!-- capsule-v2 -->
# Feature-flag admission ladder — how do you gate experimental features with renamed/graduated/dead flag semantics?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does the Linter validate constructor flags so renames transparently forward, graduations warn, and abandoned flags hard-fail?

## flags.js tables + Linter flag processing
**Path/Symbol:** `lib/shared/flags.js:activeFlags/inactiveFlags/getInactivityReasonMessage` (:28–86) + `lib/linter/linter.js:Linter.constructor` flag loop (:762–790) + `hasFlag(flag)` (:816–818).
**Signature:** `new Linter({ flags: string[] })`; inactive entries are `{description, replacedBy: string|null|undefined}`.
**Data Shape:** three-state `replacedBy` — STRING = rename (forward + warn), `null` = graduated to default behavior (warn only), `undefined` = abandoned (THROW).

### Decisive source
```js
flags.forEach(flag => {
  if (inactiveFlags.has(flag)) {
    const data = inactiveFlags.get(flag);
    const message = `The flag '${flag}' is inactive: ${getInactivityReasonMessage(data)}`;
    if (typeof data.replacedBy === "undefined") throw new Error(message);   // dead ⇒ loud
    if (typeof data.replacedBy === "string") processedFlags.push(data.replacedBy); // rename forwarding
    warningService.emitInactiveFlagWarning(flag, message);                  // typed ESLintInactiveFlag_<flag>
    return;
  }
  if (!activeFlags.has(flag)) throw new Error(`Unknown flag '${flag}'.`);
  processedFlags.push(flag);
});
// env merge (eslint-helpers.js:1325): ESLINT_FLAGS comma-split, Set-dedup, ENV FIRST then API flags
```

**Flow:** merge env+API flags → admit each through the ladder → store processed list in internal slots; runtime queries via `hasFlag`.
**Invariant:** unknown ≠ inactive — unknown throws immediately, inactive follows the replacedBy tri-state; forwarded replacement means downstream code checks ONLY the NEW name. The warning TYPE encodes the original flag name (`ESLintInactiveFlag_${flag}`), letting tools filter per-flag. WarningService defaults `emitWarning = globalThis.process?.emitWarning ?? (() => {})` so the same class runs in non-Node runtimes without throwing.
**Probe:** `tests/lib/eslint/eslint.js` (:445–540 hasFlag suite incl. env-merge :480, whitespace/duplicate env values :503/:515, replaced-flag forwarding :516); `tests/lib/services/warning-service.js` (:24–102 emitWarning assertions; :104–133 process-less safety).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "activeFlags inactiveFlags getInactivityReasonMessage hasFlag", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.linter.Linter.hasFlag" });
```

## Verdict
Adopt the tri-state replacedBy ladder for any feature-flag registry that must survive renames and graduations; adapt table location; omit env merging if you have no CLI surface.
