<!-- capsule-v2 -->
# Total name-heuristic mock — how can an endpoint mock NEVER reject an unknown call?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** a vendored SPA calls hundreds of endpoints; how does the mock stay total so bootstrap never dies on an unmapped path?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/server.ts:smartDefault` (93-123) AND `packages/app/src/pas-server.ts:smartDefault` (172-204) — deliberately duplicated per shim.
**Signature:** `function smartDefault(name: string): unknown`.
**Data Shape:** pure name->value classifier with a four-tier ladder: list-ish substrings -> `[]`; is/can/check/should prefixes + `exists` -> `true`; count/getdaily/getlimit substrings -> `0`; get/save/update/delete/create/set/remove/add/do/send/clean/close/change/try prefixes + `token` -> `null`; everything else -> `{}`. THE TWO COPIES DIFFER in the list tier's vocabulary: server matches BARE plural-resource nouns anywhere in the name (`campaigns lists tags actions results member activity statistics profiles people organizations tasks pending draft messages chats collections limits working global tips exports templates subscriptions orders billinginfos linkedinaccounts newinstances proxies workspaces invites workgroups`) because it classifies REST path segments (`/lh-backend/v2/<plural-resource>`); pas requires GET-PREFIXED forms (`getcampaigns getlists ... getsource getexports`) because it classifies dotted RPC method names. Concrete divergence: `startRunningCampaigns` -> `[]` on the server twin (contains "campaigns") but `{}` on the PAS twin ("getcampaigns" absent).

### Decisive source
```ts
// server.ts 93-123 (bare-noun list tier):
if (lower.includes("search") || lower.includes("campaigns") || /* ...plurals... */ lower.includes("workgroups")) return [];
// pas-server.ts 172-204 (get-prefixed list tier):
if (lower.includes("search") || lower.includes("getcampaigns") || /* ...getX forms... */ lower.includes("getexports")) return [];
if (lower.startsWith("is") || lower.startsWith("can") || lower.startsWith("check") ||
    lower.startsWith("should") || lower.includes("exists")) return true;
if (lower.includes("count") || lower.includes("getdaily") || lower.includes("getlimit")) return 0;
if (lower.startsWith("get") || /* ...write verbs... */ lower.includes("token")) return null;
return {};
```
**Flow:** unmatched /lh-backend path logs then answers smartDefault(path); PAS rpc/ipc:invoke falls through specificResult switch to smartDefault(method). Specific overrides always win; heuristics are only the total fallback floor. Precedence is LIST-SUBSTRING FIRST — a name hitting both the list and count tiers returns [] (live-probed pass 1: getTasksCount -> [], NOT 0) — then boolean prefixes, then count substrings, then verb-nulls.
**Invariant:** the mock NEVER returns 404/rejects — an unknown RPC resolves with something type-plausible, so SPA init chains survive; ordering matters exactly as tiered above. The duplication is intentional surface-typing, not an accident: REST segments and dotted RPC names need different list vocabularies — but it IS drift-prone, so porters must keep each copy's vocabulary tied to its surface.
**Probe:** no direct unit test exists (coverage caveat). Pass-1 live probes against the running service on ephemeral ports: unmatched `/lh-backend/v2/definitelyNotAnEndpoint` -> 200 `{}`; `/v2/getTasksCount` -> `[]` (list-substring branch outranks count branch). ERRATUM FIXED this pass: an earlier revision of this Probe line wrongly claimed `getTasksCount` returned `0` while the Flow line already said `[]` — the Flow line was right; this pass re-verified against source order (list tier precedes count tier in BOTH copies) and re-executed the Retrieve below at pin 60bf4a3e.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ultireaaach",
  qualified_name: "ultireaaach.packages.app.src.pas-server.smartDefault" });
// observed this pass: pas-server.ts 172-204, callers 3, get-prefixed list vocabulary incl. "getsource"
```

## Verdict
Adopt the total-fallback pattern for any large unknown API surface you must impersonate. Adapt each copy's verb list to ITS OWN surface grammar (path segments vs method names) rather than sharing one list. Watch the duplication: two copies can drift — if you port both shims, either extract ONE module parameterized by list-vocabulary or encode the divergence intentionally as done here.
