<!-- capsule-v2 -->
# Email & text loader timestamp fidelity — how do Date headers and mtimes become created_at without lies?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How do EmlLoader and TextFileLoader decide an episode's timeline anchor?

## EmlLoader / TextFileLoader
**Path/Symbol:** `ingestion/src/zep_ingest/loaders/email.py:36` (`EmlLoader`), `:45` (`load`), `:28` (`_html_to_text`); `loaders/text.py:22` (`TextFileLoader`), `:37` (`load`).
**Signature:** `EmlLoader(path_or_glob)` — one episode per .eml; `TextFileLoader(path_or_glob, *, created_at=None, use_file_mtime=False)`.
**Data Shape:** Email episode body = `Email from {sender} to {recipient} (subject: {subject}):\n{body}`; metadata source_type=email, subject[:100], file_name. Text metadata: source_type=document, file_name.

### Decisive source
```python
# email.py — RFC 5322's -0000 means the sender's local offset is UNKNOWN.
parsed_date = parsedate_to_datetime(str(date_header))
if parsed_date.tzinfo is None:
    parsed_date = parsed_date.replace(tzinfo=UTC)
created_at = parsed_date.isoformat()
except ValueError: created_at = None   # surfaces via missing-timestamp warning

# text.py — copy time is not a reliable factual timestamp; mtime only on
# explicit request, WITH a warning to verify:
if created_at is None and self.use_file_mtime:
    created_at = datetime.fromtimestamp(file.stat().st_mtime, tz=UTC).isoformat()
    self.warnings.append("...using filesystem modification time as created_at
        by explicit request; verify it represents the document's source date.")
```

**Flow:** eml → stdlib BytesParser(policy=default) → prefer plain part; HTML-only mail is tag-stripped (`script/style` dropped, block tags→newlines, unescape, collapse 3+ newlines) because "tag-stripped html beats silently ingesting an empty body" → Date header parsed (bad ⇒ None ⇒ pipeline missing-timestamp warning). text → glob sorted; no match raises ConfigurationError; mtime opt-in warns.
**Invariant:** Missing/invalid timestamps must become None + warning upstream ("Zep silently defaults to ingestion time, which corrupts fact validity timelines") — never a fabricated wall-clock. -0000 preserved-as-UTC keeps ingestion alive while admitting offset ignorance.
**Probe:** `grep -c 'def test' ingestion/tests/test_email_loader.py ingestion/tests/test_text_loader.py | awk -F: '{s+=$2} END{print s}'` → ≥14.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "EmlLoader date header html fallback TextFileLoader mtime", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt header-first timestamps with honest-None fallbacks + opt-in warned mtime; adapt HTML-stripping aggressiveness to your mail mix; omit Zep metadata keys.
