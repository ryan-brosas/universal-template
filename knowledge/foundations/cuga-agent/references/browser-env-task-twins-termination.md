<!-- capsule-v2 -->
# Browser-env task twins — how do two env classes share one gymnasium 5-tuple contract while terminating episodes under different infeasibility rules?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** When you port a BrowserGym-style env, how do the Playwright-owned and extension-owned twins differ in step choreography, observation assembly, and episode-termination gating?

## ExtensionEnv vs BrowserEnvGymAsync over AbstractBrowserTask
**Path/Symbol:** `src/cuga/backend/browser_env/browser/extension_env_async.py:ExtensionEnv` (`step` 217–265, `_get_obs` 267–326, `_send_to_chat` 202–215); `src/cuga/backend/browser_env/browser/gym_env_async.py:BrowserEnvGymAsync` (`step` 438–521, `_task_validate` 523–544, ctor flag line 82/135); shared SPI `src/cuga/backend/browser_env/browser/open_ended_async.py:AbstractBrowserTask` (12–81).
**Signature:** both twins expose `async def step(self, action) -> tuple` returning the gymnasium 5-tuple `(obs, reward, terminated, truncated, info)`; the task SPI is `setup(page|None)/teardown()/validate(page|None, chat_messages) -> (reward, done, message, info)` with a seed-owned `np.random.RandomState` created in `AbstractBrowserTask.__init__`.
**Data Shape:** obs dicts carry `goal_object`, `open_pages_urls/titles`, `dom_object`, `axtree_object`, `screenshot`, `last_action(_error)`, `elapsed_time`; `info` carries `action_exec_start/stop/timeout` plus `task_info`.

### Decisive source
```python
# extension_env_async.py:262 — infeasible ALWAYS terminates (no knob)
terminated = done or self.infeasible_message_received
# gym_env_async.py:516-518 — infeasible terminates only behind the ctor flag (default True)
terminated = done or (
    self.terminate_on_infeasible and self.infeasible_message_received
)  # task or agent can terminate the episode
```
```python
# gym_env_async.py:483-493 — Playwright twin's post-action settle choreography
if self.enable_browser:
    await asyncio.sleep(0.5)      # wait for JS events to be fired (half a second)
    await self.context.cookies()  # trigger all waiting Playwright callbacks on the stack (hack)
    await self._wait_dom_loaded()
    await self._active_page_check()
```
```python
# extension_env_async.py:280-281 — failed ping ⇒ bare None, NOT an obs dict
if not await self.extension_communicator.ping():
    return
```

**Flow:** both twins leave action execution as a commented-out placeholder (`gym_env_async.py:462-472`) — actions run through higher-level tools/providers, never inside `step()`. The Playwright twin settles after each action (0.5s JS-event sleep → `context.cookies()` deliberately to flush pending Playwright callbacks → DOM-loaded wait → active-page safety check) and its `_task_validate` backs up/restores `page` + `page_history` around task validation because validate() may navigate. The extension twin validates with `page=None` (no Playwright at all), sends chat messages fire-and-forget via `send_request(..., timeout=0.05)` because queue delivery IS the transport (the response never comes and must not block), and builds observations purely from extension extractions via `ExtensionProcessor`.
**Invariant:** termination gating differs BY DESIGN — ExtensionEnv treats any infeasibility report as terminal unconditionally, while the gym twin gates it behind `terminate_on_infeasible` (default True). A porter who "unifies" the two rules changes benchmark semantics. And `_get_obs` returning bare `None` after a failed ping is a contract: callers treat falsy obs as no-observation; do not "fix" it into an empty dict.
**Probe:** executed against the repo venv (see **Executed**) — checks the ctor default, extracts the literal termination line from each `step()` source, and drives a dead-communicator `ExtensionEnv._get_obs()` (via `object.__new__`) to confirm the `None` return.
**Executed:** `cd $REFERENCE_ROOT/cuga-agent && PYTHONPATH=src .venv/bin/python -c "…"` asserting (1) `inspect.signature(BrowserEnvGymAsync.__init__).parameters['terminate_on_infeasible'].default is True`, (2) `'terminate_on_infeasible' not in getsource(ExtensionEnv.step)` and the terminated-line equals `done or self.infeasible_message_received`, (3) `asyncio.run(env._get_obs()) is None` → printed `OK: gating asymmetry + None-obs contract confirmed`.
**Coverage caveat:** no upstream direct test covers either env file (grep over `tests/` finds zero references); the synthetic probe above stands in.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "ExtensionEnv OpenEndedTaskAsync terminated infeasible observation", limit: 10 });
```
(Executed pre-write: 19 hits led by `OpenEndedTaskAsync.{__init__,setup,teardown,validate}` and `ExtensionEnv.{step,_get_obs,reset}`; `trace_path` on `ExtensionEnv.step` outbound resolves `_get_obs`/`_send_to_chat`/communicator protocol methods and `AbstractBrowserTask.validate`, callers_total 0.)

## Verdict
Adopt the one-SPI-two-twins split (task objects own randomness and viewport config; env twins own transport), the settle choreography order (sleep → cookies-flush → dom-loaded → page check), and per-twin termination policy kept explicit. Adapt the settle timings and chat-message timeout to your transport. Omit nothing structural in the 5-tuple ordering — downstream planners read it positionally.
