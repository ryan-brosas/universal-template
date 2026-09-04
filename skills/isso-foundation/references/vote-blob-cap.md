<!-- capsule-v2 -->
# Bloomfilter voter blob — how are duplicate votes stored in 256 bytes per comment?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Why does voting cap at exactly 142 and how does the voters blob stay consistent with the counters?

## In-row bloom filter
**Path/Symbol:** `isso/db/comments.py:Comments.vote` (lines 359–398); `isso/utils/__init__.py:Bloomfilter` (lines 57–112).
**Signature:** `vote(upvote: bool, id, remote_addr) -> dict | None`; `Bloomfilter(array=None, elements=0, iterable=())`.
**Data Shape:** `voters` column = BLOB of a 256-byte bytearray; k=11 SHA-256-derived probes; `MAX_LIKES_AND_DISLIKES = 142`.

### Decisive source
```python
MAX_LIKES_AND_DISLIKES = 142

rv = self.db.execute("SELECT likes, dislikes, voters FROM comments WHERE id=?", (id,)).fetchone()
...
if likes + dislikes >= MAX_LIKES_AND_DISLIKES:
    ...
    return {"likes": likes, "dislikes": dislikes, "message": message}

bf = Bloomfilter(bytearray(voters), likes + dislikes)
if remote_addr in bf:
    ...denied...
bf.add(remote_addr)
self.db.execute(
    ["UPDATE comments SET",
     "    likes = likes + 1," if upvote else "dislikes = dislikes + 1,",
     "    voters = ?WHERE id=?;"],
    (memoryview(bf.array), id),
)
```

**Flow:** load counters+blob → hard-deny at ≥142 total votes (bloom false-positive rate crosses 1e-3 there — see class docstring) → membership probe denies repeat voters → add + write back blob WITH the incremented count. Denied votes return current counts plus a human-readable `message` key instead of raising.
**Invariant:** The blob is only meaningful together with its `elements` count (`likes + dislikes`) because bloom filters can't be enumerated; a porter who increments counts without rewriting the blob (or vice versa) corrupts dedupe silently. The migration rung v0→v1 exists precisely to re-mint blobs minted by an older buggy signature.
**Probe:** `grep -c MAX_LIKES_AND_DISLIKES isso/db/comments.py` (`3`) and `grep -c 'likes + dislikes >= MAX_LIKES_AND_DISLIKES' isso/db/comments.py` (`1`) and `grep -c 'voters = ?WHERE' isso/db/comments.py` (`1`).
**Test:** `isso/tests/test_vote.py:testTooManyLikes` (142 ceiling pinned by looping 256 distinct IPs), `testSelfLike`, `testVoteOnNonexistentComment`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "vote voters Bloomfilter remote addr", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the probabilistic per-row voter set when storage per comment must stay O(1). Adapt the cap to your filter's FP budget; keep cap == documented FP knee. Omit the quirky `?WHERE` spacing only if you don't copy the SQL strings verbatim.
