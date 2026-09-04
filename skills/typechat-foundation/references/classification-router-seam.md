<!-- capsule-v2 -->
# Classification router — how do you compose classify-then-dispatch over translators, and where exactly does it break?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** What is the sanctioned pattern for routing one user request to one of N schema-bound agents, and what are the failure edges the examples leave open?

## Two-stage router pair (py/ts twins)
**Path/Symbol:** `python/examples/multiSchema/router.py:16-50` (`TextRequestRouter`, `route_request` :31-50); `typescript/examples/multiSchema/src/router.ts:15-75` (`createAgentRouter`, `routeRequest` :49-74); validating schema `classificationSchema.ts:10-13`.
**Signature:** py `route_request(self, line: str)`; ts `createAgentRouter<T extends object>(model, schema, typeName): AgentRouter<T>` with `registerAgent(name, agent)` / `routeRequest(request)`.
**Data Shape:** ONE dedicated translator whose whole schema is a single classification field (`task_kind: Annotated[str, "Describe the kind of task to perform."]` py / `taskType: string` ts); a registry mapping class name → {description, handler}.

### Decisive source
```py
classes_str = json.dumps(self._current_agents, indent=2, default=lambda o: None, allow_nan=False)
prompt_fragment = F"""Classify ""{line}"" using the following classification table:
'''
{classes_str}
'''"""
result = await self._translator.translate(prompt_fragment)
...
target = self._current_agents[result["task_kind"]]
await target.get("handler")(line)
```
**Flow:** serialize the registry AS the prompt table → translate through a single-field classifier schema → look up the returned class → dispatch. The registry is rebuilt into the prompt on EVERY request, so registration is dynamic while the translator stays fixed.
**Invariant:** THE CLASS UNION IS OPEN IN BOTH PORTS — `task_kind`/`taskType` is plain `string`; validation cannot reject an unregistered class. TS mitigates by seeding a `"No Match"` table member (:27-30) plus an unknown-task handler (:34-37, compared at :59), but an invented non-"No Match" class still hits `router._agentMap[agentName]` → undefined → TypeError at dispatch; Python has NO escape member and crashes with raw `KeyError` (:49). Second trap: py serializes handler CALLABLES into the prompt via `default=lambda o: None` — the model sees `"handler": null`, which keeps the table prompt-safe but means the prompt shape silently depends on json.dumps fallback behavior. Third divergence: py passes the classify prompt as the REQUEST (so the repair fence wraps it in `'''`), ts passes it as an ASSISTANT-role preamble section (`translate(request, [{role:"assistant", content: fullRequest}])`) — different conversation shapes for the same intent. Registration semantics also differ: ts silently ignores duplicate names (`if (!router._agentMap[name])` :40), py overwrites.
**Probe:** no upstream tests for either router (examples-only plane). Static pins executed: `grep 'default=lambda o: None|allow_nan=False' router.py`=1 @32; `grep '"No Match"' router.ts`=2 @28,59; `grep 'taskType: string' classificationSchema.ts`=1 @12.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"router classify intent route agent schema","limit":6}'
// rank1-2 TextRequestRouter.route_request / routeRequest; AgentRouter interface rank7
```

## Verdict
Adopt the single-purpose-classifier + dynamic-prompt-table composition and the callable→null serialization trick; adapt by CLOSING the union yourself (Literal enum of registered names refreshed per request, or post-validate against the registry) because both upstream ports leave the unknown-class crash open; omit the assistant-preamble variant unless matching TS conversation shapes matters. Coverage caveat: zero upstream tests; evidence is whole-file source reads of both twins plus the 13-line schema.
