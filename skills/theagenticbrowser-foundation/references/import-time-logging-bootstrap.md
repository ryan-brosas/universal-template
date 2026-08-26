<!-- capsule-v2 -->
# Import-time logging bootstrap — why must logger configuration run at import, and how do you stop duplicate handlers and noisy libraries?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you configure one shared handler for app + chatty libraries so every module's `from ... import logger` is already wired?

## Module-level configure_logger() with strip-all-handlers reconfiguration and library hijack
**Path/Symbol:** `core/utils/logger.py` (`:37-84` configure + `:84` module-level call; `:87-94` set_log_level re-export).
**Signature:** `def configure_logger(level: str = "INFO") -> None` / `def set_log_level(level: str) -> None`.
**Data Shape:** Env knobs read at configure time: `LOG_LEVEL` (uppercased, overrides the argument), `LOG_MESSAGES_FORMAT` (`"json"` → pythonjsonlogger JsonFormatter, anything else → ANSI CustomFormatter). Library loggers force-joined to the same handler: `openai`, `autogen`.

### Decisive source
```python
# :45-56 — env wins over args; strip EVERY handler before adding one
level = os.getenv("LOG_LEVEL", level).upper()
log_format = os.getenv("LOG_MESSAGES_FORMAT", "text").lower()
logger = logging.getLogger()                 # ROOT logger, not __name__
for handler in logger.handlers:
    logger.removeHandler(handler)
...
# :71 — belt-and-braces second clear after setFormatter
logger.handlers = []
logger.addHandler(handler)

# :75-80 — chatty libs share the SAME handler object
http_loggers = ["openai", "autogen"]
for http_logger in http_loggers:
    lib_logger = logging.getLogger(http_logger)
    lib_logger.setLevel(logging.INFO)
    lib_logger.handlers = []
    lib_logger.addHandler(handler)

configure_logger()   # :84 — runs at IMPORT TIME
```
**Flow:** any module importing `core.utils.logger` triggers full configuration before its first log line — there is no init() call to forget. Reconfiguration (`set_log_level`) is idempotent BECAUSE of the double handler-strip: without it, every call would stack another StreamHandler and duplicate every line. The `openai`/`autogen` loggers get their own handlers cleared and inherit the root handler so SDK traffic flows through the same format gate. Module bottom silences `matplotlib.pyplot` + two PIL loggers to WARNING (:101-103); `__all__ = ["logger", "set_log_level"]` defines the public surface.
**Invariant:** Configure at import time and make reconfiguration handler-idempotent. Note the subtlety: the module-level `logger = logging.getLogger(__name__)` (:10) exists for direct import, but `configure_logger` configures the ROOT — child loggers propagate to it, which is why stripping root handlers fixes duplicates everywhere.
**Probe:** `grep -n "^configure_logger()" core/utils/logger.py` → `84`; `grep -c "removeHandler" core/utils/logger.py` → `1`; `grep -n 'handlers = \[\]' core/utils/logger.py` → lines `71` (root, after setFormatter) and `79` (inside the lib loop — one line serves openai+autogen); `grep -n "LOG_LEVEL\|LOG_MESSAGES_FORMAT" core/utils/logger.py` → `43(doc), 45, 46, 59(comment)`; `grep -n "setLevel(logging.WARNING)" core/utils/logger.py` → `101, 102, 103`. Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "configure_logger JsonFormatter CustomFormatter handlers", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt: import-time bootstrap, double-strip idempotent reconfig, shared-handler library hijack for openai/autogen, WARNING-silencing of image libs. Adapt: format strings and the library list to your stack. Omit: commented-out httpx/httpcore debug lines. Coverage caveat: no upstream tests; probes line-pinned at pin `71daa28`.
