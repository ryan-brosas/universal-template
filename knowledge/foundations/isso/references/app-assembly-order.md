<!-- capsule-v2 -->
# App assembly order — what must exist before an isso app can serve, and what fails boot?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `isso`. **Question:** In what order are db/signer/mixin/notifiers/views wired, and which boot failures are fatal vs warned?

## Isso.__init__ + make_app pre-wrapper half
**Path/Symbol:** `isso/__init__.py:Isso.__init__` (:98-124); `make_app` :166-203 (wrapper chain :204-232 owned by cors-suburi-stack).
**Signature:** `Isso(conf)`; `make_app(conf=None, threading=True, multiprocessing=False, uwsgi=False)`.
**Data Shape:** dynamic `class App(Isso, <Mixin>)` built per flag; exactly one mixin flag allowed.

### Decisive source
```python
self.db = db.SQLite3(conf.get("general", "dbpath"), conf)
self.signer = URLSafeTimedSerializer(self.db.preferences.get("session-key"))  # key LIVES in DB
self.markup = html.Markup(conf)
self.hasher = hash.new(conf.section("hash"))
super(Isso, self).__init__(conf)          # mixin: lock + cache (+ purge thread)

subscribers = []
for backend in conf.getlist("general", "notify"):
    if backend == "stdout":
        subscribers.append(Stdout(self))
    elif backend in ("smtp", "SMTP"):
        smtp_backend = True
    else:
        logger.warning("unknown notification backend '%s'", backend)
if smtp_backend or conf.getboolean("general", "reply-notifications"):
    subscribers.append(SMTP(self))         # reply-notifications FORCES SMTP even if notify=stdout

self.urls = Map()
views.Info(self)                           # views self-register routes by construction
comments.API(self, self.hasher)

# make_app: fatal vs warn at boot
if not any((threading, multiprocessing, uwsgi)):
    raise RuntimeError("either set threading, multiprocessing or uwsgi")
if not any(conf.getiter("general", "host")):
    logger.error("No website(s) configured, Isso won't work.")
    sys.exit(1)
for host in conf.getiter("general", "host"):      # HEAD probe, warn-only on failure
    with http.curl("HEAD", host, "/", 5) as resp:
        if resp is not None:
            break
else:
    logger.warning("unable to connect to your website, ...")
```

**Flow:** conf → SQLite db → signer (needs the DB-stored session-key, so db MUST come first) → markup → hasher → mixin super init (lock/cache/purge) → notifier resolution → `Signal(*subscribers)` → empty URL Map filled by view constructors as a side effect. `make_app` then picks the runtime mixin, refuses an empty host list with exit(1), and HEAD-probes each configured site (5 s timeout) warning — never failing — when unreachable.
**Invariant:** Ordering is load-bearing: signer-before-db is impossible; mixin-before-views gives view handlers their lock/cache. Unknown notify backends warn; only missing-host config and zero mixins abort boot. The `@threaded` purge start inside the mixin is fire-and-forget (`thread.start_new_thread`, no join handle).
**Probe:** `grep -c 'subscribers.append(SMTP(self))' isso/__init__.py` → `1`; `grep -c 'No website(s) configured' isso/__init__.py` → `1`.
**Test:** no direct upstream unit for assembly order (coverage caveat); exercised implicitly by every client fixture that constructs an App.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "isso", query: "Isso init signer subscribers Signal Map views Info API", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordering discipline (store → key material → cross-cutting mixin → self-registering views) and the fatal/warn split for external dependencies. Adapt notifier discovery to your plugin system. Omit the implicit-SMTP coupling unless reply notifications are also your product.
