<!-- capsule-v2 -->
# Multi-site dispatch — how does one WSGI process host several independent Isso instances?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How are per-site configs mounted and how does the prefix interact with SubURI?

## Dispatcher
**Path/Symbol:** `isso/dispatch.py:Dispatcher` (lines 17–46) + module-level ISSO_SETTINGS handling (49–63).
**Signature:** `Dispatcher(*confs)` mounts each config under `"/" + conf.get("general", "name")`.
**Data Shape:** ISSO_SETTINGS = directory (globbed `*.cfg`) or `;`-separated file list; missing names are SKIPPED with a warning, not fatal.

### Decisive source
```python
for i, path in enumerate(confs):
    conf = config.load(default, path)
    if not conf.get("general", "name"):
        logger.warning("unable to dispatch %r, no 'name' set", confs[i])
        continue
    self.isso["/" + conf.get("general", "name")] = make_app(conf)
super(Dispatcher, self).__init__(self.default, mounts=self.isso)

def __call__(self, environ, start_response):
    # clear X-Script-Name as the PATH_INFO is already adjusted
    environ.pop("HTTP_X_SCRIPT_NAME", None)
    return super(Dispatcher, self).__call__(environ, start_response)

def default(self, environ, start_response):
    resp = Response("\n".join(self.isso.keys()), 404, content_type="text/plain")
```

**Flow:** each cfg becomes a fully wrapped app at its name prefix; the dispatcher strips HTTP_X_SCRIPT_NAME because DispatcherMiddleware already consumed the mount prefix (leaving it would double-strip inside SubURI); the 404 default helpfully lists configured site names.
**Invariant:** Site identity = `[general] name`; two configs with no name silently don't serve. Each site keeps its OWN DB, signer, cache — zero shared mutable state across sites.
**Probe:** anchor `grep -c 'unable to dispatch' isso/dispatch.py` (`1`).
**Test:** no dedicated test file for dispatch.py (coverage caveat; exercised only in production topologies).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Dispatcher mounts ISSO_SETTINGS name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt name-keyed app mounting for multi-tenant single-process hosting. Adapt discovery to your config store. Preserve the header-pop — it documents a real double-prefix trap.
