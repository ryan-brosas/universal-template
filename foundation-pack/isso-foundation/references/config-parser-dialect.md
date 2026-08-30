<!-- capsule-v2 -->
# IssoParser config dialect — how do human time strings, lists, and env vars flow through INI?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What do getint/getlist/getiter add over ConfigParser, and what validation happens at load?

## IssoParser + load() linter
**Path/Symbol:** `isso/config.py:IssoParser` (86–132), `timedelta` (17–47), `load` (148–196).
**Signature:** `getint(section, key)` accepts `"15m"`-style durations (returns total seconds); `getlist` splits on commas; `getiter` yields non-empty lines.
**Data Shape:** interpolation=None (% safe passwords); allow_no_value=True; `os.path.expandvars` applied to EVERY value.

### Decisive source
```python
def timedelta(string):
    keys = ["weeks", "days", "hours", "minutes", "seconds"]
    regex = "".join(["((?P<%s>\\d+)%s ?)?" % (k, k[0]) for k in keys])
    kwargs = {}
    for k, v in re.match(regex, string).groupdict(default="0").items():
        kwargs[k] = int(v)
    rv = datetime.timedelta(**kwargs)
    if rv == datetime.timedelta():
        raise ValueError("invalid human-readable timedelta")

def get(self, section, key, **kwargs):
    return os.path.expandvars(super().get(section, key, **kwargs))

# load(): unknown-option detection by set-difference of (section, option) pairs
for item in setify(parser).difference(a):
    logger.warning("no such option: [%s] %s", *item)
    if item == ("general", "session-key"):
        logger.info("Your `session-key` has been stored in the database ...")
```

**Flow:** default-file read first → user file overlaid → set-difference flags typos as "no such option" warnings with migration hints (`server.host/port`, `smtp.ssl`) → smtp fromaddr gets a display name if bare → public-endpoint trailing slash auto-stripped with warning. Every getter expands `$VARS` so secrets come from the environment.
**Invariant:** A zero-length duration is INVALID (raises) — this is what lets getint fall through to real ints; the default From name ("Ich schrei sonst!") exists because SMTP requires a display name. Session-key lives in the DB since v2; config copies are dead but warned.
**Probe:** `grep -c 'invalid human-readable timedelta' isso/config.py` (`2`); `grep -cF 'os.path.expandvars(value)' isso/config.py` (`1`); `grep -c 'Ich schrei sonst!' isso/config.py` (`1`).
**Test:** `isso/tests/test_config.py` (full suite incl. env-var and list parsing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "IssoParser getlist getiter timedelta expandvars", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt duration-tolerant ints + typo-linting loader for any INI-configured service. Adapt regex units. Keep expandvars-on-get — it's how 12-factor secrets enter without code changes.
