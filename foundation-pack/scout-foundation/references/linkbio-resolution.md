<!-- capsule-v2 -->
# Link-in-bio cross-platform identity — how do you resolve one username across four hosts and map links back to social handles?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How does scrape_all try every link-in-bio host safely, and how are raw links classified into website vs social handles vs mailto email?

## URL-template registry + first-hit probe + three-way link classification
**Path/Symbol:** `app/scrapers/linktree.py:PLATFORMS` (:29-34), `scrape_all` (:57-63), `_scrape_profile` (:66-113), `_extract_socials` (:231-256), `_extract_website` (:259-273), `_extract_email_from_links` (:276-282).
**Signature:** `PLATFORMS: dict[name → 'https://host/{username}']`; `_extract_socials(links: List[Dict]) -> Dict[str, str]`.
**Data Shape:** social regex map (10 platforms): e.g. `'twitter': r'(?:twitter|x)\.com/([^/?]+)'`, `'discord': r'discord\.(?:gg|com/invite)/([^/?]+)'`, `'youtube': r'youtube\.com/(?:@|c/|channel/)?([^/?]+)'`.

### Decisive source
```python
def scrape_all(username):
    for platform in PLATFORMS.keys():          # dict order = probe order
        result = _scrape_profile(username, platform)
        if result:
            return result                       # first host with a page wins
    return None

def _extract_website(links):
    social_domains = ['instagram.com', ..., 'linktr.ee', ...]
    for link in links:
        url = link.get('url', '')
        if url.startswith('http') and not url.startswith('mailto:'):
            if not any(domain in url.lower() for domain in social_domains):
                return url                      # first NON-social http link = "their site"

# email priority inside every parser:
'email': _extract_email_from_links(links) or _extract_email(bio)
```

**Flow:** per username, each host URL is fetched until one returns 200 with parseable content; 404s are debug-level (expected when the user isn't on that host). Links harvested from any parser get classified three ways: mailto: → email (highest priority, beats bio sniffing); first non-social http(s) link → `website` (the field enrichment later deep-scrapes); regex-matched platform handles → `socials{}` which the interactive exporter flattens to `social_<platform>` columns.
**Invariant:** classification ORDER matters — mailto before bio-regex means a mailto link on the page always outranks an email merely mentioned in text; the social-domain exclusion list must include the link-in-bio hosts THEMSELVES (stan.store/linktr.ee/linkr.bio/bio.link) or the profile's own page becomes its "website" — a self-referential scrape loop. First-hit-wins across hosts is safe because usernames rarely collide AND each parser gates on real content.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "_extract_website\|_extract_socials\|mailto:" app/scrapers/linktree.py` pins :144/:180/:220 and helpers; graph retrieval resolves `Scout.app.scrapers.linktree.scrape_all`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "linktree scrape_all socials website extract", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the template-registry + first-hit multi-host probe and the mailto→website→socials classification ladder for identity resolution across hosted pages; adapt the platform regex map to your targets; omit nothing — but re-pin the exclusion list whenever you add a host so self-reference stays blocked.
