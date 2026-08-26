<!-- capsule-v2 -->
# Comment export plane — how do you dump an isso DB read-only without the app stack?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `isso`. **Question:** How does the contrib exporter rebuild threads and order them without touching isso code or the write path?

## dump_comments.main
**Path/Symbol:** `contrib/dump_comments.py:main` (:67-97), `print_comment` (:100-118), `parse_args` (:121-133). Second graph entry point beside `isso.isso.main`.
**Signature:** `main()` over `Comment` namedtuple `(uri, id, parent, created, text, author, email, website, likes, dislikes, replies)`; one SQL JOIN `comments ⋈ threads ON comments.tid = threads.id`.
**Data Shape:** raw `sqlite3.connect(args.db_path)` — NO isso imports; flags: `--sort-by-last-reply`, `--url-prefix`, `--no-colors`.

### Decisive source
```python
comments_per_id = {comment.id: comment for comment in comments}
root_comments, sort_date = [], None
for comment in comments:
    if comment.parent:  # reply → attach to parent IN MEMORY
        comments_per_id[comment.parent].replies.append(comment)
        if args.sort_by_last_reply and (sort_date is None or comment.created > sort_date):
            sort_date = comment.created
    else:
        root_comments.append(comment)
        if sort_date is None or comment.created > sort_date:
            sort_date = comment.created
root_comments_per_sort_date[sort_date] = root_comments
# threads print chronologically by their sort_date key

# observed pin quirk in print_comment — REPLACE, not append:
if comment.likes:
    popularity = "+{.likes}".format(comment)
if comment.dislikes:
    if popularity:
        popularity += "/"
    popularity = "-{.dislikes}".format(comment)   # overwrites "+N": "+3/-1" never renders
```

**Flow:** fetchall once → bucket rows by `uri` → per uri build id→comment map, hang replies off parents, track thread date (root created, or max(root, last reply) with `--sort-by-last-reply`) → print threads sorted by that date, replies indented two levels. Colorama is optional: import failure swaps in a `ColorFallback` stub whose `__getattr__` returns `""`; `--no-colors` rebinds the globals.
**Invariant:** Strictly read-only (single SELECT, no app/config/signer machinery). Reply attachment trusts `parent` pointing at an existing sibling row — orphaned parents silently drop replies. The popularity overwrite is pin-exact behavior, not a rendering contract.
**Probe:** `grep -c 'replies.append(comment)' contrib/dump_comments.py` → `1`; `grep -c 'popularity = "-{.dislikes}"' contrib/dump_comments.py` → `1`.
**Test:** none upstream — contrib/ has no test coverage (coverage caveat; Makefile.test does not reach it).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "isso", query: "dump comments namedtuple uri replies sort_by_last_reply colorama", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-SELECT + in-memory reassembly for read-only exports of threaded stores. Adapt output formatting freely. Omit nothing from the parent-pointer guard if your store allows dangling parents.
