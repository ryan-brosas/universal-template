<!-- capsule-v2 -->
# Moderation purge loop — how do abandoned pending comments expire?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What deletes stale mode-2 comments and under which runtime mixins does it run?

## purge-after sweeper
**Path/Symbol:** `isso/db/comments.py:Comments.purge` (lines 432–437); drivers `isso/core.py:ThreadedMixin.purge` (68–73) / `uWSGIMixin.__init__` (104–120).
**Signature:** `purge(delta)` deletes `mode=2 AND ? - created > ?`; threaded driver loops `purge(delta); time.sleep(delta)`.
**Data Shape:** `delta` = `[moderation] purge-after` parsed via config.getint's timedelta support.

### Decisive source
```python
# db layer
self.db.execute(["DELETE FROM comments WHERE mode = 2 AND ? - created > ?;"], (time.time(), delta))
self._remove_stale()

# core.ThreadedMixin
@threaded
def purge(self, delta):
    while True:
        with self.lock:
            self.db.comments.purge(delta)
        time.sleep(delta)
```

**Flow:** with moderation enabled, app startup spawns a daemon thread sweeping pending comments older than purge-after every interval, holding the SAME app lock writers use; each sweep also runs `_remove_stale` so tombstones orphaned by purges collapse too. uWSGI deployment replaces the thread with `uwsgi.add_timer(1, timedelta)` + one immediate run.
**Invariant:** Only mode-2 rows are ever purged — published and tombstoned content is immutable from this path. Lock discipline: purge shares the writer lock, never runs concurrently with add/update/delete.
**Probe:** `grep -c 'time.sleep(delta)' isso/core.py` (exactly `1`).
**Test:** no direct unit for the loop (background-thread coverage caveat); `Comments.purge` SQL exercised in test_db ladder indirectly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "purge moderation delta timer sleep", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt periodic mode-scoped sweeps sharing the write lock. Adapt trigger (thread vs scheduler). Omit nothing from the mode predicate.
