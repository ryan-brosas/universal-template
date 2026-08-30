<!-- capsule-v2 -->
# Import dispatch + autodetect — how does `isso import` choose a parser and guard re-imports?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What is the format-sniffing protocol and the non-empty-DB interaction?

## dispatch()
**Path/Symbol:** `isso/migrate.py:dispatch` (lines 335–356) + `autodetect` (321–332); CLI wiring `isso/__init__.py:main` (271–283).
**Signature:** `dispatch(type, db, dump, empty_id=False)`; autodetect peeks one buffer.
**Data Shape:** sniff needles: `'xmlns="http://disqus.com'` → Disqus; regex `http://wordpress.org/export/(1\.\d)/` → WordPress (+namespace version capture); leading `[{` → Generic JSON.

### Decisive source
```python
if db.execute("SELECT * FROM comments").fetchone():
    if input("Isso DB is not empty! Continue? [y/N]: ") not in ("y", "Y"):
        raise SystemExit("Abort.")
...
else:
    with io.open(dump, encoding="utf-8") as fp:
        cls = autodetect(fp.read(io.DEFAULT_BUFFER_SIZE))
if cls is None:
    raise SystemExit("Unknown format, abort.")
if cls is Disqus:
    cls = functools.partial(cls, empty_id=empty_id)
cls(db, dump).migrate()
```

**Flow:** interactive continue-prompt on any existing comment row (imports are append-y, not transactional) → explicit `-t` type or one-buffer sniff → unknown ⇒ exit with message → Disqus gets the empty-id workaround threaded through partial application. The `import` subcommand also force-disables the guard (`conf.set("guard", "enabled", "off")`) so rate limits never reject bulk rows, and `--dry-run` swaps in a temp DB path.
**Invariant:** Sniffing happens on RAW bytes (one io.DEFAULT_BUFFER_SIZE read) — parsers must tolerate truncated context. Autodetect order matters: Disqus needle before WP regex before JSON prefix.
**Probe:** `grep -c 'xmlns="http://disqus.com' isso/migrate.py | head -1` (`1`).
**Test:** `isso/tests/test_migration.py:test_detection` (all three detectors + unknown).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "autodetect dispatch import Disqus WordPress generic", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt peek-buffer sniffing with explicit-type override and a destructive-import prompt. Adapt needles to your formats. Keep guard-off during imports — bulk inserts otherwise trip your own rate limiter.
