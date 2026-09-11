
`<!-- capsule-v2 -->`
# Update extractor family — how do I flatten scattered update envelopes into post rows WITHOUT $type constants?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory `open-linkedin-api`. **Question:** how are raw company/profile update envelopes turned into flat post dicts, and what breaks first?

## Envelope → post-row extractors
**Path/Symbol:** `utils/helpers.py:get_urn_from_raw_update` (:15–22), `append_update_post_field_to_posts_list` (:134–161), `get_update_content` (:59–83), `get_update_author_profile` (:86–110). Callers: `Linkedin.get_company_updates`/:1012–1063, profile/feed updates walkers.
**Signature:** `get_urn_from_raw_update(raw_string: str) -> str`; `append_update_post_field_to_posts_list(d_included: Dict, l_posts: List, post_key: str, post_value: str) -> List[Dict]`; `get_update_content(d_included, base_url) -> str`; `get_update_author_profile(d_included, base_url) -> str`.
**Data Shape:** each `included[]` row is ONE field-fragment of a post (commentary text, actor urn, reshare pointer); fields accumulate into a list of row-dicts keyed by plain names (`author_name`, `content`, …) — no $type filtering anywhere in this family.

### Decisive source
```python
def get_urn_from_raw_update(raw_string):          # urn:li:fs_updateV2:(<urn>,GROUP_FEED,...)
    return raw_string.split("(")[1].split(",")[0] # composite-URN tuple split

def append_update_post_field_to_posts_list(d_included, l_posts, post_key, post_value):
    elements_current_index = len(l_posts) - 1
    if elements_current_index == -1:
        l_posts.append({post_key: post_value})            # seed first row
    else:
        if not post_key in l_posts[elements_current_index]:
            l_posts[elements_current_index][post_key] = post_value  # fill LAST row
        else:
            l_posts.append({post_key: post_value})        # key repeats => NEW row

def get_update_content(d_included, base_url):
    try:
        return d_included["commentary"]["text"]["text"]   # normal post
    except KeyError:
        return ""
    except TypeError:
        try:                                              # reshared post pointer
            urn = get_urn_from_raw_update(d_included["*resharedUpdate"])
            return f"{base_url}/feed/update/{urn}"
        except KeyError:
            return "IMAGE"
        except TypeError:
            return "None"
```

**Flow:** iterate included[] fragments → per fragment compute (key, value) with a get_update_* extractor → append through the last-row-or-new-row kernel → output is N ordered post dicts whose field COMPLETION depends entirely on envelope iteration order.
**Invariant:** the assembler is ORDER-DEPENDENT streaming join — a value lands on the LAST row unless that key already exists there, then it opens the NEXT row; sorting or reordering fragments before appending corrupts row boundaries. The content ladder's sentinel vocabulary (`""` / feed-URL-for-reshares / `"IMAGE"` / `"None"`) is load-bearing for downstream CSV consumers — do not replace with None/null without auditing consumers. Composite URNs split positionally (`split("(")[1].split(",")[0]`), never regex. Author routing maps actor urn substring → `/company/{id}` vs `/in/{id}` via `split(":")[-1]`.
**Probe:** no upstream tests (runner block recorded). Byte-exact grep resolves :22 (tuple split) / :157 (last-row key check) / :78 (reshare pointer):
```bash
grep -n 'split("(")[1]|post_key in l_posts|resharedUpdate' open_linkedin_api/utils/helpers.py
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "append_update_post_field_to_posts_list", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_urn_from_raw_update", limit: 5 });
```

## Verdict
Adopt the last-row-or-new-row streaming assembler and the positional composite-URN split for any envelope whose rows are scattered field fragments; adapt field keys and sentinel strings to your consumers; omit the $type-free design when porting INTO typed environments — there, prefer included-envelope-hydration's exact-$type filter. Contrast: voyager-dual-collection-sort covers the ORDER+CONTENT stitch for the main feed; this family covers company/update feeds where NO sort exists. Caveat: source-grounded only.
