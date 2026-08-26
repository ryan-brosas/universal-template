<!-- capsule-v2 -->
# Voyager dual-collection feed sort — the API returns order and content in TWO disconnected collections; how do I rebuild a chronologically sorted, promotion-free post list?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c` (`linkedin.py:_get_list_feed_posts_and_list_feed_urns` :1579–1655, consumed by `get_feed_posts` :1656–1672; `utils/helpers.py:parse_list_raw_urns` :164–176, `parse_list_raw_posts` :179–219, `append_update_post_field_to_posts_list` :134–161, `get_list_posts_sorted_without_promoted` :222–244). Codebase Memory `open-linkedin-api`. **Question:** when the feed endpoint hands back one array of sorted URNs and a separate unsorted array of payloads, what is the join/purge/sort contract that yields a clean timeline?

## Dual-collection paging + ordered-URN replay
**Path/Symbol:** `linkedin.py:Linkedin._get_list_feed_posts_and_list_feed_urns` (:1579–1655) — while-loop over `/feed/updatesV2` with `count = Linkedin._MAX_UPDATE_COUNT` (100; comment at :1600: "If count>100 API will return HTTP 400"), params `{count, q: "chronFeed", start}`; per page it splits the response into `l_raw_urns = res.json()["data"]["*elements"]` (sorted, includes sponsored) and `l_raw_posts = res.json()["included"]` (unsorted payloads). Sorting lives in `helpers.get_list_posts_sorted_without_promoted(l_urns, l_posts)`.
**Signature:** `_get_list_feed_posts_and_list_feed_urns(limit=-1, offset=0, exclude_promoted_posts=True) -> (List[Dict], List[str])`; `get_list_posts_sorted_without_promoted(l_urns, l_posts) -> List[Dict]`.
**Data Shape:** `data['*elements']`: list of raw URN strings in 'Recent' order (`get_urn_from_raw_update` strips them to activity ids). `included`: list of partial payload dicts; each post's fields arrive across SEVERAL included entries, stitched by `append_update_post_field_to_posts_list`, which appends the field into the LAST dict unless that key already exists there (key-collision ⇒ new post dict).

### Decisive source
```python
# helpers.py — fields of one post spread over multiple `included` entries:
def append_update_post_field_to_posts_list(d_included, l_posts, post_key, post_value):
    elements_current_index = len(l_posts) - 1
    if elements_current_index == -1 or post_key in l_posts[elements_current_index]:
        l_posts.append({post_key: post_value})      # new post dict on collision
    else:
        l_posts[elements_current_index][post_key] = post_value

# helpers.py — promote-purge BEFORE sort, then ordered replay:
def get_list_posts_sorted_without_promoted(l_urns, l_posts):
    l_posts[:] = [d for d in l_posts if d and "Promoted" not in d.get("old", "")]
    out = []
    for urn in l_urns:                               # urns carry the ONLY truth for order
        for post in l_posts:
            if urn in post["url"]:
                out.append(post)
                l_posts[:] = [d for d in l_posts if urn not in d.get("url", "")]
                break                                 # each payload joins exactly once
    return out                                        # leftover l_posts = promoted/unmatched
```

**Flow:** page `/feed/updatesV2` (remainder-shrunk count, same three-exit loop as voyager-pagination) → per page, extend `l_posts` from `included` via the field-append stitcher and `l_urns` from `data['*elements']` → after paging, purge promoted (banner text lands in the `"old"` field) → replay `l_urns` in order, popping the first payload whose `url` contains the URN.
**Invariant:** NEVER trust `included[]` order — `data['*elements']` is the only ordering source; the promoted filter must run BEFORE the sort sweep (it works on the payload side, and purged posts must not consume URNs); matching is URN-as-substring-of-URL and the matched dict is REMOVED so duplicate/reshared payloads can't join twice; URNs with no remaining payload (sponsored/promoted) silently drop — that is the purge mechanism, not a bug; `count` is hard-capped at 100 because larger pages are a server-side HTTP 400, not a soft degradation.
**Probe:** no upstream tests in this repo — coverage caveat recorded (consistent with every other open-linkedin-api capsule). Graph anchors resolve: search_graph `_get_list_feed_posts_and_list_feed_urns`, `get_list_posts_sorted_without_promoted`, `parse_list_raw_posts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_list_posts_sorted_without_promoted", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "_get_list_feed_posts_and_list_feed_urns", limit: 5 });
```

## Verdict
Adopt the split (order collection vs payload collection), the stitch-by-key-collision assembler, and the purge-then-replay join; adapt the field extractors (`get_update_author_name/content/url/...`) to your target entity; omit the `"Promoted" not in d["old"]` banner-text heuristic where an explicit sponsor flag exists in fresher API shapes. Distinct from voyager-pagination (loop mechanics only) and feed-post-urn-scan (DOM variant of the same idea). Caveat: source-grounded only; endpoint/decorationId strings rotate against live LinkedIn.
