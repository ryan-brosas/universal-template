<!-- capsule-v2 -->
# Lists and code — are lists indented and code fenced correctly?

**Source:** Google Markdown style guide §Lists, §Code. **Question:** Do nested lists and code blocks survive editing and render with language highlighting?

## List seam
**Path/Symbol:** ordered/unordered lists in docs.
**Signature:** lazy numbering for long lists; 4-space nested indent.
**Data Shape:** single-line items may use minimal spacing.

### Decisive pattern
```markdown
1.  Install dependencies.
1.  Configure the service:
    1.  Copy `config.example.yaml` to `config.yaml`.
    1.  Set `project_id`.
1.  Run verification.

*   Bullet with wrapped text that continues on the next line with a
    four-space indent.
*   Next bullet.
```

**Flow:** long/mutable ordered lists use repeated `1.` → nested content indented 4 spaces from margin → short stable lists may use `1. 2. 3.`.
**Invariant:** irregular one-space nested bullets fail review on multi-line items.
**Probe:** render preview shows correct nesting; source columns align at 4-space boundary.

## Fenced code seam
````markdown
Run the checker:

```bash
bazel test //foo:bar --test_filter=CaseName \
  --test_output=errors
```

Field names like `foo_bar_whammy` use inline `backticks` in prose.
````

**Flow:** fenced blocks with explicit language → prefer fences over 4-space indent blocks → escape fake URLs/paths with backticks → shell continuations use trailing `\`.
**Invariant:** indented code blocks without language and missing fence language tag fail review.
**Probe:** markdownlint fenced-code-language rule; highlighter renders language.

## Code in lists seam
````markdown
*   Step one.

    ```python
    def configure(project_id: str) -> None:
        ...
    ```

*   Step two.
````

**Flow:** indent opening fence to stay inside list item (typically 4 spaces from list start).
**Invariant:** unindented fence breaking list numbering fails review.
**Probe:** rendered HTML keeps list + code block grouped.

## Verdict
Lazy numbering, 4-space nesting, fenced code with language tags. Learning note: `markdown-style-learning-note.md`.
