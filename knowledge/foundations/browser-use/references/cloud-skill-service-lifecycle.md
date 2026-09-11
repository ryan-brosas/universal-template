<!-- capsule-v2 -->
# Cloud skill service lifecycle — env-gated lazy fetch with a TWO-MODE init latch

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you lazily fetch vendor "skills" from a cloud API into an agent runtime so a failing cloud never wedges or spams the run?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/skills/service.py`: `SkillService.__init__` (:22-37), `async_init` (:39-138), `get_skill` (:140-152), `get_all_skills` (:154-163), `execute_skill` (:165-277), `close` (:279-285). Exactly two constructors in the repo (graph CALLS edges): `agent/service.py Agent.__init__` and `beta/service.py Agent.__init__` — beta never registers skills (inert param at this pin).
**Signature:** `__init__(skill_ids: list[str | Literal['*']], api_key: str | None = None)`; `async get_skill(skill_id) -> Skill | None`; `async execute_skill(skill_id, parameters: dict | BaseModel, cookies: list[Cookie]) -> ExecuteSkillResponse`.
**Data Shape:** cache `dict[str, Skill]`; `_client: AsyncBrowserUse | None`; `_initialized: bool`. Env gate raises synchronously: `ValueError('BROWSER_USE_API_KEY environment variable is not set')`.

### Decisive source
```python
# :49-52 — client construction sits OUTSIDE the try; only fetch/conversion failures latch
self._client = AsyncBrowserUse(api_key=self.api_key)
try:
    ...
# :135-138 — post-construction failure poisons the latch ON PURPOSE ("avoid retry loops")
except Exception as e:
    logger.error(f'Error during skill initialization: {type(e).__name__}: {e}')
    self._initialized = True  # Mark as initialized even on failure to avoid retry loops
    raise
```

**Flow:** construct (env-gate) -> first `get_skill`/`get_all_skills`/`execute_skill` auto-calls `async_init` -> wildcard `'*'` fetches ONLY page 1 of `page_size=100` with a loud warning ("avoid LLM tool overload"); explicit IDs paginate ≤5 pages, early-stopping when all requested ids are found or a short page arrives -> filter `status=='finished'` (is_enabled filtered server-side) -> per-item `Skill.from_skill_response` conversion errors log-and-SKIP -> mark initialized.
**Invariant:** THE LATCH HAS TWO MODES (probe-corrected this pass): (A) failure INSIDE try (where a real SDK 401 lands — first `list_skills` call) sets `_initialized=True` then re-raises, so every later `get_skill` returns cache-miss `None` without retrying; (B) failure of the `AsyncBrowserUse` CONSTRUCTOR itself (:50, pre-try) leaves `_initialized=False`, so EVERY call re-attempts init and re-raises. `close()` resets `_client=None` + `_initialized=False` as the recovery valve. Execution failures NEVER raise: `execute_skill` returns `ExecuteSkillResponse(success=False, error=...)`; cache miss raises `ValueError('Skill {id} not found in cache. Available skills: [...]')`.
**Probe:** from repo root `.venv/bin/python -c`: env-less constructor → exact ValueError; stub `service.AsyncBrowserUse` to raise in `list_skills` → first get_skill raises, `_initialized True`, second → `None`, client kept; stub to raise in `__init__` → not latched, second re-raises; `close()` resets both (executed this pass; outputs in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "SkillService get_skill execute_skill lifecycle cache", limit: 10 });
```
Executed: rank-1/2 `SkillService.execute_skill` :165-277 and `SkillService.get_skill` :140-152.

## Verdict
Adopt the two-constructor gate (sync env check + async lazy init), the wildcard page-1 cap with explicit-IDs pagination ladder, log-and-skip per-item conversion, and the execution-returns-error-response (never raise) contract. Adapt the latch to YOUR failure boundary: if your client constructor can fail (bad key format, missing dep), decide explicitly whether that should retry per call (browser-use's pre-try behavior) or latch like fetch failures. Omit the browser-use SDK specifics. DRIFT HAZARD: cookie-param handling in `execute_skill` is dead code under the pin's own dependency — see skill-cookie-param-injection before porting any `'cookie'` string comparison.
