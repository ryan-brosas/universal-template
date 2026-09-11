<!-- capsule-v2 -->
# Nested-position & work-time parsing — how do I parse a LinkedIn experience entry that holds multiple roles at one company, and normalize its date-range strings?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (`scrapers/person.py`). Codebase Memory `joeyism-linkedin-scraper`. **Question:** what DOM-shape detection and date-string grammar turn one profile entity into either one Experience or a list of nested Experiences?

## Nested vs flat entity detection + date grammar
**Path/Symbol:** `linkedin_scraper/scrapers/person.py:PersonScraper._parse_experience_item` (:278–385), `_parse_nested_experience` (:387–485), `_parse_work_times` (:487–519), `_parse_education_times` (:730–756). **Signature:** `_parse_experience_item(item) -> Experience | list[Experience] | None`; `_parse_work_times("2000 - Present · 26 yrs 1 mo") -> ("2000","Present","26 yrs 1 mo")`.
**Data Shape:** an entity has `[logo_link, detail_link]`; nestedness is detected by whether `detail_children[1]` contains a `.pvs-list__container` (a second paged list of positions). Work-times grammar: split on `·` → date-range (`from - to`) + duration; education grammar: split on ` - ` → from/to, single year → both equal.

### Decisive source
```python
# nestedness = presence of an inner paged list under the detail container
has_nested_positions = False
if len(detail_children) > 1:
    nested_list = await detail_children[1].locator(".pvs-list__container").count()
    has_nested_positions = nested_list > 0
if has_nested_positions:
    return await self._parse_nested_experience(item, company_url, detail_children)
# else: flat single-role parse reading aria-hidden spans positionally

# work-times grammar
parts = work_times.split("·")            # "2000 - Present · 26 yrs 1 mo"
times = parts[0].strip(); duration = parts[1].strip() if len(parts) > 1 else None
if " - " in times:
    date_parts = times.split(" - ")
    from_date = date_parts[0].strip(); to_date = date_parts[1].strip() if len(date_parts) > 1 else ""
```

**Flow:** read the entity's `[logo_link, detail_link]` → inspect `detail_children[1]` for an inner `.pvs-list__container` → if present, recurse into `_parse_nested_experience` (company name from the first detail's first aria-hidden span, then one Experience per nested `.pvs-list__paged-list-item`, each reading position title/work-times/location from its own aria-hidden span stack) → if absent, parse the flat single role from the outer span stack → always normalize dates via the shared grammar.
**Invariant:** nested detection MUST be structural (presence of an inner list), never heuristic on text — a company with one role and a company with three roles share the same outer card shape; only the inner `.pvs-list__container` distinguishes them. The `aria-hidden="true"` spans are the stable text source (screen-reader text avoids the duplicated visible text LinkedIn renders).
**Probe:** `tests/test_person_scraper.py` covers the PersonScraper flow behind the session fixture; the date grammars are pure functions with no network dependency. Coverage: person.py `no_recorded_issue`+`metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_parse_nested_experience", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_parse_work_times", limit: 5 });
```

## Verdict
Adopt the structural nested-detection and the `·`/` - ` date grammars (shared across experience and education); adapt the aria-hidden span ordering (fragile to LinkedIn DOM changes); omit the bring_to_front focus hack. Probe caveat: extraction is source-grounded; the pure date parsers are unit-testable in isolation.
