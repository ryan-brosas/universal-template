<!-- capsule-v2 -->
# CLI bootstrap ladder — how does argv+env become a running isso server?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `isso`. **Question:** Which config source wins, which server runtime serves which `listen` URL, and what does boot log?

## main(): env-over-flag + listen-protocol ladder
**Path/Symbol:** `isso/__init__.py:main` (:235-313); gevent gate :32-41; log wiring :285-293.
**Signature:** `main()` — argparse subcommands `import`/`run`, global `-c` (default `/etc/isso.cfg`).
**Data Shape:** `conf_file = os.environ.get("ISSO_SETTINGS") or args.conf` — the env var OVERRIDES the flag; config = `config.load(config.default_file(), conf_file)` overlay.

### Decisive source
```python
# module import time — only when launched as the `isso` executable
if sys.argv[0].startswith("isso"):
    try:
        import gevent.monkey
        gevent.monkey.patch_all()
    except ImportError:
        pass

# [general] log-file: ONE FileHandler shared by two loggers, then silence propagation
logger.addHandler(handler)
logging.getLogger("werkzeug").addHandler(handler)
logger.propagate = False
logging.getLogger("werkzeug").propagate = False

if conf.get("server", "listen").startswith("http://"):
    host, port, _ = urlsplit(conf.get("server", "listen"))
    try:
        from gevent.pywsgi import WSGIServer
        WSGIServer((host, port), make_app(conf)).serve_forever()
    except ImportError:
        run_simple(host, port, make_app(conf), threaded=True,
                   use_reloader=conf.getboolean("server", "reload"))
elif conf.get("server", "listen").startswith("unix://"):
    sock = conf.get("server", "listen").partition("unix://")[2]
    try:
        os.unlink(sock)
    except OSError as ex:
        if ex.errno != errno.ENOENT:
            raise
    wsgi.SocketHTTPServer(sock, make_app(conf)).serve_forever()
else:
    logger.error("server.listen must specify a protocol of http:// or unix://")
    sys.exit(1)
```

**Flow:** parse argv → `ISSO_SETTINGS` beats `-c` → config file must exist (else exit 1) → default-file overlay load → (`import` branch: see import-dispatch-autodetect) → optional dual-logger file handler → dispatch on `server.listen` protocol: `http://` tries gevent then falls back to werkzeug's threaded dev server; `unix://` strips the prefix with `partition`, unlinks a stale socket tolerating ONLY `ENOENT`, serves on `SocketHTTPServer`; any other scheme is fatal. Each branch builds its own `make_app(conf)`.
**Invariant:** The same env var has TWO semantics — here a single config path overriding `-c`; in `dispatch.py` a multi-site dir/`;`-list (see multisite-dispatch capsule). Socket cleanup re-raises every non-ENOENT errno. Bare-host `listen` values are rejected at boot.
**Probe:** `grep -c 'ISSO_SETTINGS") or args.conf' isso/__init__.py` → `1`; `grep -c 'partition("unix://")' isso/__init__.py` → `1`.
**Test:** no direct upstream test for `main()` (coverage caveat); import branch behavior pinned via `isso/tests/test_migration.py` per import-dispatch-autodetect.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "isso", query: "main subparser listen unix gevent run_simple", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt env-over-flag precedence and the protocol→runtime ladder for any embeddable service CLI. Adapt logger names/socket paths to your host. Omit the gevent patch gate unless you ship an executable literally named `isso`.
