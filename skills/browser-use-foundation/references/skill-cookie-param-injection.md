<!-- capsule-v2 -->
# Skill cookie-param injection — LLM-schema exclusion + execution-time re-injection (DRIFT-PINNED)

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** when a vendor-defined action needs a browser credential the LLM must never see, how do you hide it from the model schema yet still fulfill it at execution time?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/skills/views.py`: `MissingCookieException` (:9-20), `Skill.parameters_pydantic` (:49-61), `output_type_pydantic` (:63-71); `browser_use/skills/service.py` `execute_skill` cookie block (:194-224); `browser_use/agent/service.py` handler catch (:881-888).
**Signature:** `parameters_pydantic(self, exclude_cookies: bool = False) -> type[BaseModel]`; `execute_skill(..., cookies: list[Cookie])`; `MissingCookieException(cookie_name: str, cookie_description: str)`.
**Data Shape:** `ParameterSchema{name, type, required, description}`; live jar reduced to `{cookie['name']: cookie['value']}`; `required` defaults True when the API omits the flag.

### Decisive source
```python
# views.py :58-59 — intended contract: hide cookie params from the LLM-facing schema
if exclude_cookies:
    parameters = [param for param in parameters if param.type != 'cookie']

# service.py :203-209 — execution side re-checks and injects from the LIVE cookie jar
is_required = cookie_param.required if cookie_param.required is not None else True
if is_required and cookie_param.name not in cookie_dict:
    raise MissingCookieException(cookie_name=cookie_param.name,
                                 cookie_description=cookie_param.description or 'No description provided')

# agent/service.py :883-888 — duck-typed catch BY CLASS NAME STRING (import-free)
if type(e).__name__ == 'MissingCookieException':
    error_msg = f'Missing cookies ({cookie_name}): {cookie_description}'
    return ActionResult(extracted_content=None, error=error_msg)
```

**Flow:** registration builds the LLM param model with `exclude_cookies=True` -> per-step availability report recomputes missing required cookies against the live jar -> at execution the agent handler fetches fresh cookies per call, `execute_skill` raises `MissingCookieException(name, description)` for a missing required one, else injects `{name: value}` into the params dict before validation -> the handler converts a raise into a GUIDED `ActionResult.error`, closing the remediation loop (model reads which cookie to log in for).
**Invariant:** the two halves must agree on ONE type test. DRIFT (probed live again this pass): under the pin's own dependency (`browser-use-sdk==3.4.2`, pyproject :48) `ParameterSchema.type` is a `ParameterType` ENUM — `<ParameterType.cookie: 'cookie'>` — so BOTH `'cookie'` string comparisons are dead: exclusion no-ops (the cookie field STAYS in the LLM schema as a required `str`; probed: excluded-fields list still contains `session_cookie`), injection/required-gating never fire, the availability report stays empty, and an empty jar surfaces as an unguided pydantic-derived ValueError ("Parameter validation failed for skill T:\n - session_cookie: Field required") instead of MissingCookieException guidance. Porters must compare `param.type.value` (or isinstance the enum).
**Probe:** `.venv/bin/python -c` from repo root: build `Skill` with a `type='cookie'` ParameterSchema; assert `parameters_pydantic(exclude_cookies=True).model_fields` STILL contains it (drift evidence); `str(MissingCookieException('session_cookie', 'log into the dashboard'))` → `"Missing required cookie 'session_cookie': log into the dashboard"` with `.cookie_name` attribute (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "skill parameters pydantic exclude cookies MissingCookieException", limit: 10 });
```
Executed: rank-1 `Skill.parameters_pydantic` :49-61; converter rank-3.

## Verdict
Adopt the DESIGN: credentials as out-of-band params excluded from the model schema and injected at execution from live runtime state, with a typed exception that renders into guided remediation text, and the import-free class-name-string catch when the raising module may not be importable. Adapt the injection source (cookies → your host's credential store). Omit nothing blindly: RE-CHECK the enum-vs-string type test against YOUR sdk version — this exact plane shipped dead under browser-use 0.13.8 because of it.
