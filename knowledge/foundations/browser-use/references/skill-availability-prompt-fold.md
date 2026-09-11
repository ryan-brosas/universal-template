<!-- capsule-v2 -->
# Skill availability prompt fold — per-step remediation text from live runtime state, total-function shaped

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you tell an LLM which of its actions are currently unusable AND what would make them usable, without ever breaking the step?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/service.py`: `Agent._get_unavailable_skills_info` (:918-989); call sites (:1115-1118 per-step, threaded into `create_state_messages` :1142).
**Signature:** `async def _get_unavailable_skills_info(self) -> str` — TOTAL function.
**Data Shape:** input = cached skills + live cookie jar as `{name: value}`; output = rendered text or `''`; per-skill record `{id, title, description, missing_cookies: [{name, description}]}`.

### Decisive source
```python
# :920-922 + :988-989 — every exit is a string; exceptions degrade to ''
if not self.skill_service:
    return ''
...
except Exception as e:
    self.logger.error(f'Error getting unavailable skills info: {type(e).__name__}: {e}')
    return ''

# :975-985 — slug FIRST so the model connects the disabled action to its remedy
slug = self._get_skill_slug(skill_obj, skills) if skill_obj else skill_info['title']
lines.append(f'\n  • {slug} ("{title}")')
lines.append(f'    Description: {skill_info["description"]}')
lines.append('    Missing cookies:')
for cookie in skill_info['missing_cookies']:
    lines.append(f'      - {cookie["name"]}: {cookie["description"]}')
```

**Flow:** each step (only when a skill service exists) -> fetch all skills -> reduce the CURRENT browser cookie jar to `{name: value}` -> for each skill with cookie-typed params, list required ones absent from the jar (`required` defaults True when the API omits the flag) -> render bullet lines keyed by the SAME slugs the registration used -> inject into state messages. No unavailable skills / empty cache / any error ⇒ `''`.
**Invariant:** recomputed EVERY step against LIVE state (cookies change mid-run after logins — availability is a function of now, not of registration time); never raises into the step loop; names must match registered action names or the model cannot connect symptom to remedy. DRIFT note: at this pin the underlying `p.type == 'cookie'` test is dead (enum drift — see skill-cookie-param-injection), so this report renders empty in practice; the CONTRACT below is still the design to port.
**Probe:** `.venv/bin/python -c` from repo root: run unbound over a stub self with `skill_service=None` → returns `''` (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "unavailable skills info missing cookies prompt", limit: 10 });
```
Executed during discovery: rank-1 `_get_unavailable_skills_info` :918-989.

## Verdict
Adopt the shape: a total per-step "why can't you act" reporter whose output folds into the existing state message rather than a separate channel, named so the model maps it onto the action surface one-to-one. Adapt the predicate (cookies → any runtime precondition: auth, quota, network reachability). Omit the cookie specifics. Pair with action-timeout-hang-guard's philosophy: context enrichment must never be able to fail the step.
