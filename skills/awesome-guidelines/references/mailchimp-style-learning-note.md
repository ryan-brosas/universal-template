# Mailchimp content style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `mailchimp-style-*.md` capsules, `mailchimp-content-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Mailchimp Content Style Guide](https://styleguide.mailchimp.com/) (primary) | CC BY-NC 4.0 public guide; principles clear/useful/friendly/appropriate |
| [TL;DR](https://styleguide.mailchimp.com/tldr/) (primary) | Voice priorities; person-first; grammar/web/a11y/i18n summary |
| [Voice and Tone](https://styleguide.mailchimp.com/voice-and-tone/) (primary) | Plainspoken, genuine, translator role; dry humor; tone follows reader state; active voice |
| [Grammar and Mechanics](https://styleguide.mailchimp.com/grammar-and-mechanics/) (primary) | Hierarchy, concise/specific, serial comma, numbers/dates/money/time, punctuation, Mailchimp capitalization |
| [Writing About People](https://styleguide.mailchimp.com/writing-about-people/) (primary) | Person-first; singular they; gender/disability/race/age guidance; audience/contacts as people |
| [Web Elements](https://styleguide.mailchimp.com/web-elements/) (primary) | Headings sentence case; titles title case; buttons verbs/sentence case; forms minimal; links; SEO human-first |
| [Writing for Accessibility](https://styleguide.mailchimp.com/writing-for-accessibility/) (primary) | No directional language; nested headings; plain language; alt text; forms; descriptive links |
| [Writing for Translation](https://styleguide.mailchimp.com/writing-for-translation/) (primary) | SVO; repeat verbs/subjects; avoid -ing/ambiguous words; metric; USD/CAD codes; no slang |
| [Word List](https://styleguide.mailchimp.com/word-list/) (secondary) | email/login/signup hyphenation; terms to avoid (master/slave, ninja, etc.) |
| `markdown-writing-practices` (secondary) | Repo Markdown layout — Mailchimp rules apply to product/marketing copy, not replacing MD structure skill |

**Scope:** **Product, marketing, and UI copy** (help, emails, web, forms). **Technical repo docs:** start with `markdown-writing-practices`; apply Mailchimp voice where user-facing prose overlaps.

**TL;DR vs detailed sections:** TL;DR once said title case for all headings and title case buttons; **Web Elements** specifies **sentence case** for headings/buttons/checkboxes and **title case** for page titles and main nav — follow Web Elements when they differ.

## Mental model

Mailchimp content quality is **plainspoken clarity with person-first respect**:

1. **Voice/tone** — human, familiar, straightforward; clarity > entertainment; active/positive; humor dry and optional.
2. **Grammar/structure** — lead with main point; short sentences; serial comma; consistent patterns; read aloud test.
3. **Inclusive people language** — singular they; avoid age/disability/gender bias; Black capitalized, white lowercase (Mailchimp rule); contacts are people.
4. **Web/a11y/i18n** — one topic per page; descriptive links (not “click here”); nested headings; alt text; translation-safe SVO and repeated verbs.

## Decision tables

### Principles & voice

| Topic | Rule |
|---|---|
| Goals | clear, useful, friendly, appropriate |
| Voice | human, familiar, friendly, straightforward, plainspoken |
| Tone | informal usually; match reader emotional state |
| Humor | dry, subtle; never forced; clarity wins |
| Active voice | default; passive only when emphasizing action recipient |
| Jargon | plain English; define technical terms briefly |
| Positive framing | prefer “do X” over “don’t fail to X” |
| Contractions | encouraged |

### Grammar & mechanics (selected)

| Topic | Rule |
|---|---|
| Structure | group related ideas; descriptive headers; most important first |
| Acronyms | spell out first use unless API/HTML-level familiar |
| Capitalization | title case vs sentence case per element type (see web) |
| Serial comma | yes (Oxford) |
| Numbers | spell out sentence-start; numerals otherwise; commas in 1,000+ |
| Dates | Saturday, January 24 (abbreviate only if space tight) |
| Time | `7 am`, `7:30 pm`; hyphen ranges; default ET for events |
| Emphasis | italics for long titles/emphasis; no underline; no bold+italic+caps stack |
| Alignment | left-align body text |

### Writing about people

| Topic | Rule |
|---|---|
| Audience/contacts | they/them; real people not “it” |
| Age/disability | mention only when relevant; no “young/old/elderly” |
| Gender | no “guys”/“girls”; neutral job words; singular they OK |
| LGBTQ+ | identity terms as modifiers not nouns; avoid homosexual/lifestyle/preference |
| Race | capitalize Black; lowercase white (Mailchimp) |
| Disability | person-first or identity-first per subject preference; avoid suffer/victim/handicapped |

### Web elements

| Element | Case / rule |
|---|---|
| Page title | title case; no end punctuation unless question |
| Headings H1–Hn | sentence case; hierarchical; keywords naturally |
| Buttons | verbs; sentence case; concise (“Log in”, “Sign up free”) |
| Checkboxes/radio | sentence case |
| Drop-down | title case menu name; sentence case items |
| Forms | title case title; sentence case fields; minimal fields; no irrelevant gender |
| Nav | title case main; sentence case sub |
| Links | link meaningful words; not “click here”; no linked punctuation |
| Lists | intro sentence; numbered when order matters |
| SEO | one topic; human-first; no keyword stuffing |

### Accessibility & translation

| Topic | Rule |
|---|---|
| Direction | no “right sidebar” — describe action |
| Headings | nested, no level skips for styling |
| Alt text | describe function or content purpose |
| Links | destination/action clear |
| Translation | active SVO; repeat parallel verbs/subjects; avoid -ing, slang, double negatives |
| Ambiguous words | caution: once, since, right, require+infinitive |
| Currency (i18n) | `25 USD` not `$25`; metric measurements spelled out |

### Word list highlights

| Prefer | Avoid |
|---|---|
| email, login (n), log in (v), sign up (v), website, OK | automagical, leverage, ninja/rockstar/wizard |
| add-on / add on | blacklist, whitelist, master/slave, grandfathered |
| defer to AP if not listed | crushing it, crazy/insane for people |

## Anti-patterns

- Passive voice by default
- Keyword stuffing for SEO
- “Click here” / “Learn more” link text
- Directional UI copy (“see panel on the right”)
- Skipped heading levels for styling
- Gender dropdown when irrelevant
- Forced humor or exclamation-heavy failure messages
- “Guys”, “girls”, ninja/rockstar job titles
- master/slave, blacklist/whitelist in new copy
- Ambiguous “once/since/right” in translation-bound text
- `-ing` pile-ups in internationalized strings
- `$25` instead of `25 USD` for global audiences
- Underline or bold+italic+caps emphasis stacks
- Writing in mascot (Freddie) voice

## Skill trace

| Artifact | Role |
|---|---|
| `mailchimp-style-voice-tone.md` | voice, tone, active/positive language |
| `mailchimp-style-grammar-structure.md` | hierarchy, numbers, punctuation, consistency |
| `mailchimp-style-inclusive-people.md` | person-first, gender, disability, race |
| `mailchimp-style-web-accessibility-i18n.md` | UI copy, a11y, translation, links |
| `mailchimp-content-practices/SKILL.md` | product/marketing copy review workflow |

## Relation to `markdown-writing-practices`

| Mailchimp content | Markdown skill |
|---|---|
| Voice, inclusive language, UI microcopy | ATX structure, fences, 80-col wrap |
| Web heading case in product pages | Single H1 doc convention |
| Link anchor text principles | Descriptive links + reference links |
| Use both when user-facing docs mix marketing voice with repo Markdown mechanics |
