<!-- capsule-v2 -->
# Event vocabulary & BrowserProfile — typed command bus + kwargs-splattering launch config

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how do agent actions reach the browser (typed events, not method calls), and how does one config object drive four different playwright launch modes?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/events.py` (667 lines): ~45 event classes on `bubus.BaseEvent`, layered as Agent→Browser commands (`NavigateToUrlEvent` :110 with `wait_until: 'load'|'domcontentloaded'|'networkidle'|'commit'`, `ClickElementEvent` :125, `TypeTextEvent` :147, `SwitchTabEvent` :169, ...), browser lifecycle (`BrowserStartEvent` :292, `BrowserKillEvent` :324, `BrowserReconnectingEvent` :474), tab events (`TabCreatedEvent` :391, `AgentFocusChangedEvent` :420, `TargetCrashedEvent` :429), storage (`SaveStorageStateEvent` :499), downloads (:544-580), captcha (:604-630); `_get_timeout(env_var, default)` (:16) per-event env-tunable timeouts; `ElementSelectedEvent.serialize_node` (:56) strips circular refs before dispatch. `browser/profile.py`: `BrowserProfile` (:574) — one pydantic model multiply-inheriting `BrowserConnectArgs, BrowserLaunchPersistentContextArgs, BrowserLaunchArgs, BrowserNewContextArgs`; `get_args()` (:895-973).
**Signature:** every action is an event with a typed result generic; handlers are `on_EventName` methods; timeouts per event via `TIMEOUT_<EventName>` env vars.
**Data Shape:** profile = superset of all playwright kwargs + custom fields (`disable_security`, `allowed_domains`, `prohibited_domains`, `block_ip_addresses`, `captcha_solver`, `demo_mode`, proxy, extensions); 100+ item domain lists auto-optimize to sets.

### Decisive source
```ts
# get_args(): compile CLI args from layers, then MERGE conflicting flags:
default_args = CHROME_DEFAULT_ARGS - set(ignore_default_args or [])
pre_conversion_args = [*default_args, *self.args,
    f'--user-data-dir=...', *(CHROME_DOCKER_ARGS if in_docker...),
    *(CHROME_HEADLESS_ARGS if headless else []),
    *(CHROME_DISABLE_SECURITY_ARGS if disable_security else []),
    *(CHROME_DETERMINISTIC_RENDERING_ARGS if deterministic_rendering else []), ...]
# --disable-features appears from multiple sources: merge values, don't clobber
for arg in pre_conversion_args:
    if arg.startswith('--disable-features='):
        disable_features_values.extend(arg.split('=',1)[1].split(','))
# dedupe preserving order, re-emit ONE merged flag
# then dict-roundtrip dedupes all other repeatable args
final_args = args_as_list(args_as_dict(non_disable_features_args))
```

**Flow:** agent/tools emit typed events → session's ResilientEventBus routes to watchdog/session handlers → results come back through the event's generic type. Launch path: BrowserProfile validates itself in `model_post_init` (devtools/headless conflicts, proxy sanity, storage-state vs user-data-dir warnings, legacy name migration) → `get_args()` layers defaults + docker + headless + security + rendering + window + extension args → merges multi-source flags → dedupes.
**Invariant:** events carry everything a handler needs (node refs sanitized of circular fields); env vars can tune any timeout without code; the profile never stores derived state — args are compiled fresh each launch; flag conflicts resolve by VALUE-MERGING (--disable-features), never last-write-wins.
**Probe:** profile tests (kwargs split per launch mode; domain-list set optimization; legacy-name copy); events tests (node serialization strips parents/children).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "NavigateToUrlEvent BrowserProfile get_args CHROME_DEFAULT_ARGS disable-features merge", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt typed result-generic events for action dispatch and a single kwargs-splat profile that compiles+merges CLI args at launch time. Adapt event bus to host.
