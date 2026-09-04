<!-- capsule-v2 -->
# Sans-IO layer discipline — what may live in flask/sansio/ and why does the split matter for porters?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What constraint defines the sansio modules, and which seams does it force upward into app.py?

## The three-module sansio core
**Path/Symbol:** `src/flask/sansio/README.md:1–6` (the contract), `scaffold.py` (800L), `app.py` (1013L), `blueprints.py` (692L); concrete twins `src/flask/{app,blueprints}.py`.
**Signature:** Scaffold base (registration decorators + errorhandler machinery + static/template path properties + `_check_setup_finished` hook); App (config/json/jinja/url_map construction + add_url_rule + handler lookup); Blueprint (record/replay).
**Data Shape:** sansio code "cannot do any IO, nor be part of a likely IO path. Finally this code cannot use the Flask globals."

### Decisive source
```
# src/flask/sansio/README.md (verbatim contract):
This folder contains code that can be used by alternative Flask
implementations, for example Quart. The code therefore cannot do any
IO, nor be part of a likely IO path. Finally this code cannot use the
Flask globals.
```

**Flow:** everything sync/async-neutral and context-free lives in sansio (Scaffold/App/Blueprint, incl. `_find_error_handler`, `add_url_rule`, `from_prefixed_env`-style config is NOT there — it imports nothing request-bound); concrete Flask/Blueprint add WSGI specifics (`wsgi_app`, dispatch pipeline, cli, weakref static route, AppGroup). Quart-style ports reuse the sansio tree wholesale.
**Invariant:** no `request`/`current_app` proxy reads inside sansio — e.g. blueprint `get_send_file_max_age` uses `current_app` and therefore lives in the CONCRETE twin; keep this boundary or your async port inherits WSGI assumptions.
**Probe:** `grep -rFc 'from .globals' src/flask/sansio/` = 0; `grep -rFc 'open(' src/flask/sansio/'` = 0; structure pinned by graph packages list (sansio modules import-free of globals).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "Scaffold App sansio blueprint base", limit: 8 });
```

## Verdict
Adopt the IO-free/globals-free layering as the porting seam map. Adapt concrete-twin contents to your server model. Omit nothing in sansio — it is deliberately minimal.
