
`<!-- capsule-v2 -->`
# Conversation participant resolution — how do I find THE one conversation with a given profile when the params serializer mangles List()?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory `open-linkedin-api`. **Question:** how is the single thread for one participant resolved, and why is the filter query hand-assembled into the URI?

## Participant-keyed conversation fetch
**Path/Symbol:** `linkedin.py:Linkedin.get_conversation_details` (:1205–1229); listing twin `Linkedin.get_conversations` (:1231–1241).
**Signature:** `get_conversation_details(profile_urn_id: str) -> Dict` (single row or `{}`); `get_conversations() -> dict` (raw envelope).
**Data Shape:** `GET /messaging/conversations?keyVersion=LEGACY_INBOX&q=participants&recipients=List({profile_urn_id})`; response elements[] of conversation rows carrying `EntityUrn`s.

### Decisive source
```python
# passing `params` doesn't work properly, think it's to do with List().
# Might be a bug in `requests`?
res = self._fetch(
    f"/messaging/conversations?\
    keyVersion=LEGACY_INBOX&q=participants&recipients=List({profile_urn_id})"
)
data = res.json()
if data["elements"] == []:
    return {}                                   # miss = EMPTY dict, not exception
item = data["elements"][0]
item["id"] = get_id_from_urn(item["entityUrn"]) # id derived from entityUrn
return item
```
(The backslash inside the f-string is Python explicit line joining — the served URL contains no whitespace; verified byte-exact at :1216–1219.)

**Flow:** participant URN id → hand-inlined List() filter in the URI → take elements[0] as THE conversation with that person → attach numeric `id` split from entityUrn before returning.
**Invariant:** List()-typed query values must be assembled INTO the URI string here because the params-dict path mis-serializes them (upstream comment; same grammar as voyager-filter-grammar-serializer). A miss returns `{}` — a DATA-SHAPED failure callers test by truthiness, not try/except. The returned id is always DERIVED from entityUrn, never trusted from caller input. Listing variant passes a plain params dict (`keyVersion=LEGACY_INBOX` only) because it has no List() value — the workaround applies ONLY where List() appears.
**Probe:** no upstream tests (runner block recorded). Byte-exact grep resolves :1218 (raw List() URI) / :1223 (empty-elements miss):
```bash
grep -n 'q=participants|elements"] == []' open_linkedin_api/linkedin.py | head -5
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_conversation_details", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_conversations", limit: 5 });
```

## Verdict
Adopt participant-keyed single-thread resolution with empty-dict misses and entityUrn-derived ids; adapt the endpoint/keyVersion per generation; omit the raw-string hack ONLY after proving your HTTP client serializes List() correctly (requests did not). Contrast: messaging-read-path-scrollers (private-api twin) pages ALL conversations through a typed timestamp-cursor scroller over the SAME LEGACY_INBOX projection — use THAT for enumeration, THIS for point lookup. Caveat: source-grounded only.
