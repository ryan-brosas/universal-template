<!-- capsule-v2 -->
# Flash messages — why does flash() re-assign the whole list, and where are consumed flashes cached?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What session-integration contract does the flash pair enforce that a naive `session.setdefault` breaks?

## flash / get_flashed_messages
**Path/Symbol:** `src/flask/helpers.py:flash` (326–357), `.get_flashed_messages` (360–399).
**Signature:** `flash(message, category="message") -> None`; `get_flashed_messages(with_categories=False, category_filter=()) -> list`.
**Data Shape:** storage key `_flashes: list[tuple[category, message]]`; per-context cache on `app_ctx._flashes`.

### Decisive source
```python
# Original implementation:
#     session.setdefault('_flashes', []).append((category, message))
# This assumed that changes made to mutable structures in the session are
# always in sync with the session object, which is not true for session
# implementations that use external storage.
flashes = session.get("_flashes", [])
flashes.append((category, message))
session["_flashes"] = flashes          # EXPLICIT reassignment marks modified

def get_flashed_messages(...):
    flashes = app_ctx._flashes
    if flashes is None:
        flashes = session.pop("_flashes") if "_flashes" in session else []
        app_ctx._flashes = flashes      # consume ONCE per context
    if category_filter:
        flashes = list(filter(lambda f: f[0] in category_filter, flashes))
```

**Flow:** write path re-writes the key so CallbackDict-based sessions (and external-store interfaces) see modification → signal message_flashed. Read path pops from session on FIRST call in a context and caches so repeated template calls return the same list without re-consuming.
**Invariant:** category_filter filters a COPY for display; consumption happens once even with multiple get calls; unfiltered vs filtered return shapes differ only by with_categories.
**Probe:** `grep -Fc 'session["_flashes"] = flashes' src/flask/helpers.py` = 1; `grep -Fc 'app_ctx._flashes = flashes' src/flask/helpers.py` = 1; tests `tests/test_basic.py::test_flashes` (:620), `tests/test_signals.py::test_flash_signal` (:139).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "flash flashed messages session", limit: 5 });
```

## Verdict
Adopt explicit-key-write + one-consumption-per-context cache. Adapt category defaults. Omit nothing.
