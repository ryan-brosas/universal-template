<!-- capsule-v2 -->
# RegisteredTool update-handle memoization — how do live rename/schema updates keep derived caches from serving stale or wrong-owner data?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A registry hands out live update handles; what does it take to invalidate memoized conversions when the key itself can change?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/mcp.ts`: `_toolInputSchemaJson` cache (:84), lazy `toolInputSchemaJson()` (:94-115), registration-time conversion + SEP-2243 scan (:829-845), rename/evict choreography inside `update` (:866-906).
**Signature:** `toolInputSchemaJson(name): Record<string,unknown> | undefined` — `undefined` = "skip validation", never a 500.
**Data Shape:** Memo slot `{[name]: jsonSchema}`; executor closure tracks CURRENT name (`name = updates.name` reassignment).

### Decisive source
```ts
update: updates => {
    // The closure's `name` tracks the CURRENT registry key, not the original
    // registration name — renaming reassigns it so subsequent paramsSchema/rename
    // invalidations evict the live slot rather than the original.
    if (updates.name !== undefined && updates.name !== name) {
        if (typeof updates.name === 'string') validateAndWarnToolName(updates.name);
        delete this._registeredTools[name];
        delete this._toolInputSchemaJson[name];
        if (updates.name) {
            // The TARGET key may already be occupied by another tool (rename has NO
            // duplicate-name guard) — drop its memo too, otherwise pre-dispatch SEP-2243
            // validation runs against the WRONG schema for this name.
            delete this._toolInputSchemaJson[updates.name];
            this._registeredTools[updates.name] = registeredTool;
            name = updates.name;
        }
    }
```
And the lazy-path contract:
```ts
} catch { return undefined; }  // conversion failure: skip validation; failure surfaces where it always has (tools/list)
```

**Flow:** register → eager convert (warn-never-throw; throw leaves slot unset) → per-request reads hit the memo (per-request-factory model would otherwise re-convert every call) → `update({paramsSchema})` evicts + regenerates executor → `rename` evicts BOTH old slot and any OCCUPIED target slot, then rebinds the closure's `name`.

**Invariant:** Registration-time conversion failure must NOT block local dev (stdio clients ignore header declarations) — warn and continue. Rename without duplicate-guard is legal here, so target-slot eviction is mandatory for correctness, not hygiene. The same converted JSON feeds `tools/list` AND pre-dispatch validation so listing and dispatch cannot diverge.

**Probe:** `packages/server/test/server/mcp.icons.test.ts` (`.update({…})` handle usage); `mcpParamValidation.test.ts` + `stdHeaderValidation.test.ts` (pre-dispatch SEP-2243 behavior); integration `mcp.test.ts` :784/:1853 (remove/disable lifecycle).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "toolInputSchemaJson _toolInputSchemaJson scanXMcpHeaderDeclarations standardSchemaToJsonSchema", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt closure-tracked-keys + two-sided memo eviction on rename + warn-never-throw conversion at the boundary; adapt to your registry; omit the MCP header-declaration vocabulary.
