<!-- capsule-v2 -->
# Debugger helper logging contract — how do in-process debug helpers stay silent until asked, yet keep working when the host Python is broken?

**Source:** JetBrains Rider installed build `RD-262.8665.400` (`plugins/cidr-debugger-plugin/bin/helpers/jb_debugger_logging.py`, 47L whole); Codebase Memory `jetbrains-rider`. **Question:** What logging contract should embeddable Python helpers follow so they cost nothing when healthy, produce full logs when diagnosed, and never spam known-benign host errors?

## The module as the decisive instance
**Path/Symbol:** `jb_debugger_logging.py:DebuggerLogging.create_logger` (:27-37), `_create_debug_log_file_handler` (:11-21), `_HashlibErrorFilter.filter` (:40-44).
**Signature:** `create_logger(name: str) -> logging.Logger`; env input `JB_PYTHON_DEBUG_LOG_PATH`.
**Data Shape:** one shared class-level FileHandler (append mode, utf-8, format `%(asctime)s.%(msecs)d %(levelname)s - #%(name)s - %(message)s`); disabled loggers get level `LOGGING_DISABLED = logging.CRITICAL + 1`.

### Decisive source
```python
new_logger.propagate = False
if cls._debug_log_file_handler is not None:
    new_logger.addHandler(cls._debug_log_file_handler)
    new_logger.setLevel(cls._debug_log_file_handler.level)
else:
    new_logger.disabled = True
    new_logger.setLevel(LOGGING_DISABLED)
...
class _HashlibErrorFilter(logging.Filter):
    def filter(self, record):
        # This error can be triggered by importing 'hashlib' from anywhere, even the standard library.
        # We ignore it because our bundled Python on macOS doesn't support 'blake2s' and 'blake2b'.
        return record.msg != "code for hash %s was not found."
logging.getLogger().addFilter(_HashlibErrorFilter())
```

**Flow:** import time: env read ONCE into a class-level handler slot, root logger gets the noise filter → every helper asks `create_logger(name)`: with env set it receives the shared DEBUG-level FileHandler; without it the logger is disabled outright (no handlers, propagation cut, level above CRITICAL).
**Invariant:** silence is the default and costs zero I/O; enabling is a single env var with no code change. The noise filter is message-EXACT (string equality against the one known-benign record), installed at the ROOT logger once per process — not per-logger config. Wrong port: filtering by logger name or substring — the shipped contract matches the exact msg template so unrelated errors survive.
**Probe:** executed GREEN against the shipped file, two processes: (1) env unset → `disabled==True` ∧ `level==CRITICAL+1`; (2) `JB_PYTHON_DEBUG_LOG_PATH=/tmp/x.log` → FileHandler@DEBUG attached, `debug("hello-probe")` lands in file, root carries exactly one `_HashlibErrorFilter`, False for the hashlib msg and True for any other message.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", query: "DebuggerLogging", limit: 6 });
// -> ...jb_debugger_logging.DebuggerLogging.create_logger Method :28-37
```

## Verdict
Adopt: env-gated single-handler logging with deny-by-default disabled loggers and a root-level exact-message noise filter for known-broken host platforms. Adapt the env name and filtered-message list to your host. Companion fact: `jb_os_type.py` (37L) exposes `HOST_OS` enum whose values ARE `platform.system()` strings incl. 'Darwin', with Unknown fallback — helpers' platform-branch vocabulary.
