<!-- capsule-v2 -->
# Config + Environ read-tracking — env vars that refuse writes after reads

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** What does Starlette's tiny config layer guarantee that os.environ + dotenv don't?

## Environ — write-after-read guard
**Path/Symbol:** `starlette/config.py:Environ` (:18-35), singleton `environ` (:44).
### Decisive source
```python
def __getitem__(self, key): self._has_been_read.add(key); return self._environ[key]
def __setitem__(self, key, value):
    if key in self._has_been_read:
        raise EnvironError(f"Attempting to set environ['{key}'], but the value has already been read.")
```
**Flow:** any read records the key; subsequent set/delete of a READ key raises. Catches the classic bug: code read a config value at import time (baked into a constant), then tests/CLI tried to mutate it and the change silently didn't propagate.
**Invariant:** only keys actually READ are frozen — writing fresh keys stays legal.
**Probe:** `tests/test_config.py::test_environ` (:112).

## Config.get — precedence ladder + typed casting
**Path/Symbol:** `starlette/config.py:Config.get` (:94-109) + `_perform_cast` (:123-140) + `_read_file` (:111-121).
**Data Shape:** lookup order `env_prefix+key in environ` → in file_values → default → KeyError("Config '{key}' is missing, and no default."). `default=undefined` sentinel distinguishes "no default" from `default=None`.
**Flow:** cast applies to ALL three sources (env, file, AND default) — a bool default True with cast=bool passes through mapping validation too; str-to-bool accepts exactly {true,1,false,0} case-insensitively, else ValueError naming key+value; failed casts re-raise as ValueError with key context (never bare int()/float() tracebacks).
**Invariant:** env_file lines strip surrounding quotes (`value.strip().strip("\"'")`) but perform NO escape handling — keep values quote-free or accept literal stripping.
**Probe:** `::test_config_types` (:12) pins every cast; `::test_config_with_env_prefix` (:137).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_perform_cast", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "Environ", limit: 5 });
```

## Verdict
Adopt the read-freeze semantics (it's ~15 lines and prevents a real class of config bugs). Adopt sentinel-default + cast-everything. Omit env_file parsing for full dotenv compatibility — this reader deliberately supports only KEY=VALUE with optional quotes.
