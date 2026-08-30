<!-- capsule-v2 -->
# Links and media — are links readable and paths stable?

**Source:** Google Markdown style guide §Links, §Images. **Question:** Do links read naturally in prose and resolve without fragile relative hops?

## Inline link seam
**Path/Symbol:** Markdown links in prose and tables.
**Signature:** meaningful link text; explicit internal paths; reference links for long URLs.
**Data Shape:** reference definitions after first use in section.

### Decisive pattern
```markdown
See the [Markdown style guide](/docs/reference/style.md) for formatting rules.

Check a [typical test result](https://ci.example.com/job/123/artifact/log.txt).

The [style guide][style-guide] repeats this rule in section 4.

[style-guide]: https://docs.example.com/long/path/to/style-guide-v2.html
```

**Flow:** wrap the phrase that describes destination — not "here" or bare URL → internal docs use explicit path `/docs/...md` → same-directory relative OK → avoid `../../` chains → reference links when URL disrupts 80-col flow.
**Invariant:** `[here](url)` and duplicated raw URL as link text fail review.
**Probe:** markdownlint link-text rules; no `](../` in diff unless same-dir exception documented.

## Reference placement seam
```markdown
## Installation

Download the bundle from [releases][rel].

[rel]: https://example.com/path/to/release-1.2.3.tar.gz

## Configuration

...
```

**Flow:** define reference link at end of section where first used → document-wide reused refs at file end.
**Invariant:** all reference defs dumped at file bottom far from first use fail review on long docs.
**Probe:** reader can find `[ref]:` within one screen of first `[ref]` usage.

## Images seam
```markdown
![Settings panel with API key field highlighted](settings-api-key.png)
```

**Flow:** images sparingly for UI navigation/screenshots → descriptive alt text for non-sighted readers → prefer showing over describing when truly easier.
**Invariant:** `![](image.png)` without alt fails review.
**Probe:** a11y spot check on pages with images.

## Verdict
Descriptive links, stable paths, reference links for length, alt on images. Learning note: `markdown-style-learning-note.md`.
